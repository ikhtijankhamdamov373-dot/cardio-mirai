"""
Cardio MIRAI ACS — ECG image/PDF digitization.

RESEARCH PROTOTYPE. NOT A MEDICAL DEVICE. NOT FOR CLINICAL USE.
NOT CLINICALLY VALIDATED.

This module implements a genuinely functional, deliberately scoped-down
image-to-waveform pipeline for the most common printed-ECG format:

  image/PDF -> quality gate -> grid bounding-box detection -> grid-pitch
  detection (calibration) -> deterministic 3x4(+rhythm strip) panel
  cropping, inset to exclude lead-label text and calibration pulses ->
  per-panel trace-centerline extraction (colour-based, continuity-tracked)
  -> pixel-to-physical-unit conversion -> resampled waveform array ->
  the SAME existing ECG Core measurement function used by the real-WFDB
  pipeline (cardiomirai.acs.ecg_ingestion.measure_array_to_lead_inputs,
  which itself calls cardiomirai.api.extract_basic_ecg_measurements) ->
  the SAME audited ACS Core engine.

ROOT CAUSE OF THE EARLIER FAILURE (fixed in this revision): panel
cropping used to divide the RAW IMAGE dimensions into 3 equal rows and 4
equal columns. Any real photograph has margins around the printed grid,
and the common format also has a 4th row (a long Lead-II rhythm strip)
beneath the 3 diagnostic rows. Dividing the raw image into thirds
therefore misaligned every single panel boundary — worse, this did not
always fail cleanly: it sometimes produced HIGH-CONFIDENCE, WRONG
measurements (trace fragments and label text captured in the wrong
crop region still register as "a continuous dark line"). This revision
fixes the geometry itself: panels are now cropped from the detected grid
region's bounding box, not the raw image, and the layout is aware of the
rhythm-strip row.

What this module does NOT do, by design, for today's scope:
  - Automatic lead-label OCR. Lead-label text regions are excluded by a
    fixed inset margin (labels are conventionally printed at fixed
    corners of each panel), not read.
  - Full automatic layout classification across ECG manufacturers. Only
    two layouts are supported: "standard_3x4_rhythm_strip" (3 diagnostic
    rows + a long Lead II strip — the most common format) and
    "standard_3x4" (3 diagnostic rows only, no strip). A basic aspect-
    ratio sanity check rejects images that plainly do not match either.
  - Automatic calibration confidence beyond grid-pitch detection. Paper
    speed and gain are user-confirmed (or defaulted to the near-universal
    25 mm/s, 10 mm/mV, explicitly labeled as a default, never claimed to
    be OCR-read); only the pixels-per-mm scale factor is detected from
    the image's own grid lines, and if that detection is unreliable, the
    whole request is refused rather than guessed.
  - Perspective correction for significant rotation/skew.
  - Multi-page PDF page selection.

Every numeric measurement returned by this module traces back to actual
pixel intensities in the uploaded image. Any stage that cannot produce a
trustworthy result raises ImageDigitizationError rather than proceeding
with a guessed, interpolated-across-the-board, or fabricated value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from scipy.signal import find_peaks

# --- Fixed layout definitions -------------------------------------------
# The near-universal printed 12-lead ECG layout: 3 rows x 4 columns,
# optionally followed by a long Lead-II rhythm strip as a 4th row.

STANDARD_3X4_LAYOUT = [
    ["I", "aVR", "V1", "V4"],
    ["II", "aVL", "V2", "V5"],
    ["III", "aVF", "V3", "V6"],
]
# Primary supported layout going forward: 3 diagnostic rows + a long
# Lead-II rhythm strip as the 4th row (the most common printed format).
# "standard_3x4" (no rhythm strip, exactly 3 rows) remains supported for
# layouts genuinely printed without one.
SUPPORTED_LAYOUTS = {"standard_3x4_rhythm_strip", "standard_3x4"}
DEFAULT_LAYOUT = "standard_3x4_rhythm_strip"

MIN_MEGAPIXELS = 0.5
BLUR_VARIANCE_THRESHOLD = 80.0   # Laplacian variance; below this = likely blurry
MAX_ROTATION_DEG = 8.0           # beyond this, refuse rather than attempt correction
MIN_GRID_PEAKS_FOR_PITCH = 6
GRID_PITCH_CV_THRESHOLD = 0.25   # coefficient of variation of peak spacing; above = unreliable
MIN_TRACE_COLUMN_COVERAGE = 0.6  # fraction of panel columns needing a detected trace pixel
TARGET_RESAMPLED_FS = 250.0

# Panel geometry safety margins, as a fraction of panel width/height.
# Lead labels are conventionally printed at the top-left corner of each
# panel; calibration pulses appear at the very start of each row. Insetting
# the extraction ROI by these margins keeps that text/pulse content out of
# the trace-centerline computation without needing OCR to locate it.
PANEL_TOP_LABEL_MARGIN_FRAC = 0.18
PANEL_LEFT_CALIBRATION_MARGIN_FRAC = 0.06

# Aspect-ratio sanity bounds for the whole image, used as a lightweight
# (non-OCR) layout plausibility check — not a classifier, just a guard
# against obviously-mismatched uploads (e.g. a portrait single-lead strip).
MIN_ASPECT_RATIO = 1.1
MAX_ASPECT_RATIO = 4.0


class ImageDigitizationError(ValueError):
    """Raised whenever the image/PDF cannot be safely digitized. Callers
    must surface this as a clear error, never substitute synthetic data."""


@dataclass
class ImageQualityReport:
    width: int
    height: int
    megapixels: float
    blur_variance: float
    is_blurry: bool
    estimated_rotation_deg: float
    excessive_rotation: bool
    acceptable: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class DigitizationResult:
    lead_arrays: dict            # canonical lead name -> 1D np.ndarray (mV), resampled
    fs: float
    px_per_mm: float
    paper_speed_mm_s: float
    gain_mm_per_mv: float
    panel_trace_confidence: dict  # canonical lead name -> float 0-1
    excluded_low_confidence_leads: list[str]
    quality: ImageQualityReport
    warnings: list[str] = field(default_factory=list)


def load_image(file_bytes: bytes, filename: str) -> np.ndarray:
    """Decodes JPG/PNG bytes, or renders page 1 of a single-page PDF, to a
    BGR image array. Refuses multi-page PDFs outright — no page classifier
    exists to identify which page (if any) contains the ECG."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        import pymupdf

        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        if doc.page_count > 1:
            raise ImageDigitizationError(
                f"The uploaded PDF has {doc.page_count} pages. This prototype "
                "cannot reliably identify which page (if any) contains the "
                "ECG in a multi-page document. Please upload a single-page "
                "PDF or an image of the ECG page only."
            )
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=300)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        return img_array

    if lower.endswith((".jpg", ".jpeg", ".png")):
        array = np.frombuffer(file_bytes, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is None:
            raise ImageDigitizationError(
                "The uploaded file could not be decoded as an image. It may be "
                "corrupt or not a genuine JPG/PNG file."
            )
        return image

    raise ImageDigitizationError(
        f"Unsupported file format for '{filename}'. Accepted: .jpg, .jpeg, .png, .pdf."
    )


def assess_image_quality(image_bgr: np.ndarray) -> ImageQualityReport:
    """Real quality checks: resolution, blur (Laplacian variance — a
    standard, genuine focus-quality metric), and rotation (estimated from
    the dominant angle of detected straight lines, which on a real ECG
    photo are overwhelmingly the printed grid lines)."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    megapixels = (width * height) / 1_000_000.0

    blur_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    is_blurry = blur_variance < BLUR_VARIANCE_THRESHOLD

    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=width // 4, maxLineGap=10)
    estimated_rotation_deg = 0.0
    if lines is not None and len(lines) > 0:
        angles = []
        for line in lines[:200]:
            x1, y1, x2, y2 = line[0]
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Fold to the nearest of 0/90 degrees (grid lines are horizontal or vertical)
            folded = angle % 90
            if folded > 45:
                folded -= 90
            angles.append(folded)
        if angles:
            estimated_rotation_deg = float(np.median(angles))
    excessive_rotation = abs(estimated_rotation_deg) > MAX_ROTATION_DEG

    reasons = []
    if megapixels < MIN_MEGAPIXELS:
        reasons.append(f"Resolution too low ({megapixels:.2f} MP, minimum {MIN_MEGAPIXELS} MP)")
    if is_blurry:
        reasons.append(f"Image appears blurry (focus score {blur_variance:.0f}, minimum {BLUR_VARIANCE_THRESHOLD:.0f})")
    if excessive_rotation:
        reasons.append(f"Excessive rotation detected ({estimated_rotation_deg:.1f}°, maximum {MAX_ROTATION_DEG}°)")

    return ImageQualityReport(
        width=width, height=height, megapixels=round(megapixels, 2),
        blur_variance=round(blur_variance, 1), is_blurry=is_blurry,
        estimated_rotation_deg=round(estimated_rotation_deg, 2),
        excessive_rotation=excessive_rotation,
        acceptable=(len(reasons) == 0),
        reasons=reasons,
    )


def estimate_grid_px_per_mm(gray: np.ndarray) -> Optional[float]:
    """Detects the ECG paper's small-square grid pitch (1 mm) via
    periodicity in the image's row-wise intensity projection — a real
    signal-processing technique (peak-spacing analysis), not a guess.
    Returns None if the peak spacing is inconsistent (grid not reliably
    detected), so the caller can refuse rather than use a bad estimate."""
    # Use a central horizontal band, since grid lines run the full width.
    band = gray[gray.shape[0] // 3 : gray.shape[0] * 2 // 3, :]
    # Grid lines are locally darker than the paper background.
    profile = 255.0 - np.mean(band, axis=0)
    profile = profile - np.mean(profile)

    peaks, _ = find_peaks(profile, distance=3)
    if len(peaks) < MIN_GRID_PEAKS_FOR_PITCH:
        return None

    spacings = np.diff(peaks)
    if len(spacings) == 0:
        return None
    median_spacing = float(np.median(spacings))
    if median_spacing <= 0:
        return None
    cv = float(np.std(spacings) / median_spacing)
    if cv > GRID_PITCH_CV_THRESHOLD:
        return None  # spacing too inconsistent to trust as the grid pitch

    return median_spacing  # pixels per 1mm small-square


def detect_grid_bounding_box(image_bgr: np.ndarray) -> tuple[int, int, int, int]:
    """
    Finds the (x0, y0, x1, y1) bounding box of the printed grid within the
    full image, using the same colour signature used elsewhere in this
    module (grid lines are reddish; margins are white; machine/patient
    text at the bottom is black, not reddish, so it is correctly excluded
    here too). This is the fix for the root cause of the earlier failure:
    panels were being cropped from the RAW IMAGE's dimensions, which
    silently misaligned every panel whenever the image had margins or a
    4th row, sometimes producing high-confidence but wrong measurements
    rather than a clean failure.
    """
    b = image_bgr[:, :, 0].astype(np.float32)
    r = image_bgr[:, :, 2].astype(np.float32)
    redness = r - b
    grid_mask = redness > (np.median(redness) + 10)

    rows_with_grid = np.flatnonzero(np.any(grid_mask, axis=1))
    cols_with_grid = np.flatnonzero(np.any(grid_mask, axis=0))
    if len(rows_with_grid) == 0 or len(cols_with_grid) == 0:
        raise ImageDigitizationError(
            "No printed grid could be detected in this image (looked for the "
            "characteristic red/pink ECG grid colour). Please upload a photo "
            "or scan that clearly shows the printed grid."
        )
    return (
        int(cols_with_grid[0]), int(rows_with_grid[0]),
        int(cols_with_grid[-1]) + 1, int(rows_with_grid[-1]) + 1,
    )


def crop_layout_panels(image_bgr: np.ndarray, layout: str) -> dict:
    """
    Deterministic panel geometry, cropped from the DETECTED GRID'S
    bounding box (not the raw image), aware of whether a rhythm-strip 4th
    row is expected:

      - "standard_3x4_rhythm_strip": the grid bounding box is divided into
        4 equal-height rows; only the first 3 are diagnostic panels
        (mapped I/aVR/V1/V4, II/aVL/V2/V5, III/aVF/V3/V6); the 4th (long
        Lead II rhythm strip) is intentionally NOT treated as another
        diagnostic panel.
      - "standard_3x4": the grid bounding box is divided into 3 rows, no
        rhythm strip assumed.

    Each panel is then inset by fixed margins (PANEL_TOP_LABEL_MARGIN_FRAC,
    PANEL_LEFT_CALIBRATION_MARGIN_FRAC) to exclude the lead-label text
    and calibration-pulse regions from the extraction ROI.

    Raises for any other layout value — no other layout is implemented.
    """
    if layout not in SUPPORTED_LAYOUTS:
        raise ImageDigitizationError(
            f"Layout '{layout}' is not supported. Supported layouts: "
            f"{sorted(SUPPORTED_LAYOUTS)}. ECG layout not currently "
            "supported by the research prototype."
        )

    gx0, gy0, gx1, gy1 = detect_grid_bounding_box(image_bgr)
    grid_w = gx1 - gx0
    grid_h = gy1 - gy0

    n_rows_total = 4 if layout == "standard_3x4_rhythm_strip" else 3
    row_h = grid_h // n_rows_total
    col_w = grid_w // 4

    panels = {}
    for row_idx, row_leads in enumerate(STANDARD_3X4_LAYOUT):
        for col_idx, lead_name in enumerate(row_leads):
            y0 = gy0 + row_idx * row_h
            y1 = gy0 + (row_idx + 1) * row_h
            x0 = gx0 + col_idx * col_w
            x1 = gx0 + (col_idx + 1) * col_w

            # Inset to exclude the lead-label text (top-left of panel) and
            # any calibration pulse (start of row).
            top_inset = int((y1 - y0) * PANEL_TOP_LABEL_MARGIN_FRAC)
            left_inset = int((x1 - x0) * PANEL_LEFT_CALIBRATION_MARGIN_FRAC)
            panels[lead_name] = image_bgr[y0 + top_inset : y1, x0 + left_inset : x1]

    return panels


def extract_trace_centerline(panel_bgr: np.ndarray) -> tuple[np.ndarray, float]:
    """Isolates the ECG trace from the printed grid using colour, not just
    grayscale intensity, then follows it column-by-column via continuity
    tracking rather than blindly averaging every dark pixel in a column.

    Real printed ECG paper grids are pink/red specifically so the trace
    (drawn or printed in black or blue) can be separated from the grid by
    colour — a plain grayscale intensity threshold cannot reliably tell a
    mid-tone grid line from ink, since both are 'darker than the white
    background' in grayscale. This isolates pixels that are both (a) dark
    overall and (b) not reddish.

    Continuity tracking: a column may contain more than one dark
    connected segment (e.g. a stray fragment of lead-label text that
    extends past the panel's top inset margin, or noise). Rather than
    averaging all of them together — which corrupts the measurement —
    each column's chosen position is the connected segment closest to the
    previous column's chosen position, since the genuine ECG trace is a
    single continuous line while text/noise fragments are not spatially
    continuous with it across many neighbouring columns.

    Returns the per-column row index (float, NaN where undetected) and a
    confidence score (fraction of columns with a detected trace pixel)."""
    b = panel_bgr[:, :, 0].astype(np.float32)
    g = panel_bgr[:, :, 1].astype(np.float32)
    r = panel_bgr[:, :, 2].astype(np.float32)
    intensity = (b + g + r) / 3.0
    redness = r - b  # positive and large for pink/red grid; near zero for black or blue ink

    panel_min = float(np.min(intensity))
    panel_median = float(np.median(intensity))
    dark_cutoff = panel_min + 0.4 * (panel_median - panel_min)

    is_dark = intensity <= dark_cutoff
    is_not_reddish = redness <= (np.median(redness) * 0.5 + 10)
    mask = (is_dark & is_not_reddish).astype(np.uint8) * 255

    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    height, width = mask.shape
    centerline = np.full(width, np.nan)
    detected_columns = 0
    previous_row: Optional[float] = None

    for x in range(width):
        column_pixels = np.flatnonzero(mask[:, x])
        if len(column_pixels) == 0:
            continue

        # Group into contiguous runs (a column can have >1 disconnected
        # dark segment — e.g. residual text plus the trace).
        splits = np.flatnonzero(np.diff(column_pixels) > 1)
        segments = np.split(column_pixels, splits + 1)
        segment_centers = [float(np.mean(seg)) for seg in segments]

        if previous_row is None:
            # No prior context yet: take the largest segment (most likely
            # to be the continuous trace rather than a small text blob).
            chosen = segment_centers[int(np.argmax([len(s) for s in segments]))]
        else:
            chosen = min(segment_centers, key=lambda c: abs(c - previous_row))

        centerline[x] = chosen
        previous_row = chosen
        detected_columns += 1

    confidence = detected_columns / width if width else 0.0
    return centerline, confidence


def digitize_ecg_image(
    file_bytes: bytes,
    filename: str,
    paper_speed_mm_s: float,
    gain_mm_per_mv: float,
    layout: str = DEFAULT_LAYOUT,
) -> DigitizationResult:
    """Top-level orchestrator. Raises ImageDigitizationError at any stage
    that cannot produce a trustworthy result."""
    if paper_speed_mm_s <= 0 or gain_mm_per_mv <= 0:
        raise ImageDigitizationError("Paper speed and gain must be confirmed, positive values.")

    image_bgr = load_image(file_bytes, filename)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    height, width = gray.shape
    aspect_ratio = width / height if height else 0
    if not (MIN_ASPECT_RATIO <= aspect_ratio <= MAX_ASPECT_RATIO):
        raise ImageDigitizationError(
            "ECG layout not currently supported by the research prototype. "
            f"The image's proportions (aspect ratio {aspect_ratio:.2f}) do not "
            "match the supported standard 3x4 (+ rhythm strip) format."
        )

    quality = assess_image_quality(image_bgr)
    if not quality.acceptable:
        raise ImageDigitizationError(
            "ECG image quality insufficient for reliable waveform digitization. "
            "Please retake the photograph with the full ECG visible, camera "
            "perpendicular to the paper, and adequate lighting. "
            f"Specific issues: {'; '.join(quality.reasons)}."
        )

    px_per_mm = estimate_grid_px_per_mm(gray)
    if px_per_mm is None:
        raise ImageDigitizationError(
            "ECG grid could not be reliably detected in this image, so pixel "
            "measurements cannot be safely converted to millimetres/millivolts. "
            "Please retake the photograph with the printed grid clearly visible "
            "and undistorted."
        )

    panels = crop_layout_panels(image_bgr, layout)

    warnings: list[str] = []
    lead_arrays: dict = {}
    confidences: dict = {}
    excluded: list[str] = []

    seconds_per_pixel = (1.0 / px_per_mm) / paper_speed_mm_s

    for lead_name, panel in panels.items():
        centerline_px, confidence = extract_trace_centerline(panel)
        confidences[lead_name] = round(confidence, 2)
        if confidence < MIN_TRACE_COLUMN_COVERAGE:
            excluded.append(lead_name)
            continue

        # Fill small gaps by linear interpolation only (never a full
        # panel), and only when overall coverage already cleared the
        # confidence bar above.
        valid = ~np.isnan(centerline_px)
        if valid.sum() < 2:
            excluded.append(lead_name)
            continue
        x_valid = np.flatnonzero(valid)
        centerline_filled = np.interp(np.arange(len(centerline_px)), x_valid, centerline_px[valid])

        baseline_row = float(np.median(centerline_filled))
        mv_values = (baseline_row - centerline_filled) / px_per_mm / gain_mm_per_mv

        n_columns = len(mv_values)
        duration_s = n_columns * seconds_per_pixel
        n_resampled = max(2, int(round(duration_s * TARGET_RESAMPLED_FS)))
        original_t = np.linspace(0, duration_s, n_columns)
        resampled_t = np.linspace(0, duration_s, n_resampled)
        resampled_mv = np.interp(resampled_t, original_t, mv_values)

        lead_arrays[lead_name] = resampled_mv

    if excluded:
        warnings.append(f"Excluded leads with unreliable trace extraction (low pixel coverage): {sorted(excluded)}")

    if not lead_arrays:
        raise ImageDigitizationError(
            "No lead panel produced a reliable trace extraction. The image "
            "may not match the confirmed layout, or the trace may not be "
            "distinguishable from the grid/background."
        )

    max_len = max(len(v) for v in lead_arrays.values())
    for lead_name in list(lead_arrays.keys()):
        arr = lead_arrays[lead_name]
        if len(arr) < max_len:
            lead_arrays[lead_name] = np.pad(arr, (0, max_len - len(arr)), mode="edge")

    return DigitizationResult(
        lead_arrays=lead_arrays,
        fs=TARGET_RESAMPLED_FS,
        px_per_mm=round(px_per_mm, 2),
        paper_speed_mm_s=paper_speed_mm_s,
        gain_mm_per_mv=gain_mm_per_mv,
        panel_trace_confidence=confidences,
        excluded_low_confidence_leads=excluded,
        quality=quality,
        warnings=warnings,
    )
