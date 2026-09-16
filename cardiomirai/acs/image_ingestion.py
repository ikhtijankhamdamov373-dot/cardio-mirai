"""
Cardio MIRAI ACS — ECG image/PDF digitization.

RESEARCH PROTOTYPE. NOT A MEDICAL DEVICE. NOT FOR CLINICAL USE.
NOT CLINICALLY VALIDATED.

This module implements a genuinely functional, deliberately scoped-down
image-to-waveform pipeline for a single, common printed-ECG layout:

  image/PDF -> quality gate -> grid-pitch detection (calibration) ->
  fixed 3x4 panel cropping -> per-panel trace-centerline extraction ->
  pixel-to-physical-unit conversion -> resampled waveform array ->
  the SAME existing ECG Core measurement function used by the real-WFDB
  pipeline (cardiomirai.acs.ecg_ingestion.measure_array_to_lead_inputs,
  which itself calls cardiomirai.api.extract_basic_ecg_measurements) ->
  the SAME audited ACS Core engine.

What this module does NOT do, by design, for today's scope:
  - Automatic lead-label OCR or layout detection. The caller must confirm
    "standard_3x4" (the only layout implemented); anything else is refused.
  - Automatic calibration confidence beyond grid-pitch detection. Paper
    speed and gain are always user-confirmed values, never inferred from
    the image; only the pixels-per-mm scale factor is detected from the
    image's own grid lines, and if that detection is unreliable, the
    whole request is refused rather than guessed.
  - Perspective correction for significant rotation/skew. Images with
    excessive detected rotation are rejected at the quality gate.
  - Multi-page PDF page selection. A PDF with more than one page is
    refused outright, since this module has no way to reliably identify
    which page (if any) contains the ECG.

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

# --- Fixed layout definition -------------------------------------------
# The near-universal printed 12-lead ECG layout: 3 rows x 4 columns.
# Confirmed by the user before use (see cardiomirai/acs/api.py); this
# module implements ONLY this layout. A rhythm-strip row beneath, if
# present, is not used for measurement (see LIMITATIONS in the delivery
# report) — panels are cropped from the top 3 rows regardless of total
# image height, which is imprecise if a rhythm strip occupies unequal
# vertical space; flagged as a known limitation, not silently corrected.
STANDARD_3X4_LAYOUT = [
    ["I", "aVR", "V1", "V4"],
    ["II", "aVL", "V2", "V5"],
    ["III", "aVF", "V3", "V6"],
]
SUPPORTED_LAYOUTS = {"standard_3x4"}

MIN_MEGAPIXELS = 0.5
BLUR_VARIANCE_THRESHOLD = 80.0   # Laplacian variance; below this = likely blurry
MAX_ROTATION_DEG = 8.0           # beyond this, refuse rather than attempt correction
MIN_GRID_PEAKS_FOR_PITCH = 6
GRID_PITCH_CV_THRESHOLD = 0.25   # coefficient of variation of peak spacing; above = unreliable
MIN_TRACE_COLUMN_COVERAGE = 0.6  # fraction of panel columns needing a detected trace pixel
TARGET_RESAMPLED_FS = 250.0


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


def crop_layout_panels(image_bgr: np.ndarray, layout: str) -> dict:
    """Fixed proportional grid slicing for the standard 3x4 layout. Raises
    for any other layout value — no other layout is implemented."""
    if layout not in SUPPORTED_LAYOUTS:
        raise ImageDigitizationError(
            f"Layout '{layout}' is not supported. Only 'standard_3x4' is "
            "implemented in this prototype; other layouts are refused "
            "rather than guessed at."
        )
    height, width = image_bgr.shape[:2]
    row_h = height // 3
    col_w = width // 4
    panels = {}
    for row_idx, row_leads in enumerate(STANDARD_3X4_LAYOUT):
        for col_idx, lead_name in enumerate(row_leads):
            y0, y1 = row_idx * row_h, (row_idx + 1) * row_h
            x0, x1 = col_idx * col_w, (col_idx + 1) * col_w
            panels[lead_name] = image_bgr[y0:y1, x0:x1]
    return panels


def extract_trace_centerline(panel_bgr: np.ndarray) -> tuple[np.ndarray, float]:
    """Isolates the ECG trace from the printed grid using colour, not just
    grayscale intensity.

    Real printed ECG paper grids are pink/red specifically so the trace
    (drawn or printed in black or blue) can be separated from the grid by
    colour — a plain grayscale intensity threshold cannot reliably tell a
    mid-tone grid line from ink, since both are 'darker than the white
    background' in grayscale. This isolates pixels that are both (a) dark
    overall and (b) not reddish (grid lines have a notably higher red
    channel than blue; true black/blue ink does not). Returns the
    per-column row index (float, NaN where undetected) and a confidence
    score (fraction of columns with a detected trace pixel)."""
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
    for x in range(width):
        column_pixels = np.flatnonzero(mask[:, x])
        if len(column_pixels) > 0:
            centerline[x] = float(np.mean(column_pixels))
            detected_columns += 1

    confidence = detected_columns / width if width else 0.0
    return centerline, confidence


def digitize_ecg_image(
    file_bytes: bytes,
    filename: str,
    paper_speed_mm_s: float,
    gain_mm_per_mv: float,
    layout: str,
) -> DigitizationResult:
    """Top-level orchestrator. Raises ImageDigitizationError at any stage
    that cannot produce a trustworthy result."""
    if paper_speed_mm_s <= 0 or gain_mm_per_mv <= 0:
        raise ImageDigitizationError("Paper speed and gain must be confirmed, positive values.")

    image_bgr = load_image(file_bytes, filename)
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

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
