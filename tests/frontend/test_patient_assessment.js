/**
 * Frontend data-flow tests for the Patient Assessment refactor.
 *
 * Run with: node tests/frontend/test_patient_assessment.js
 * Requires: npm install jsdom (in tests/frontend/, or wherever this is run from)
 *
 * These exercise the REAL index.html against a real DOM (jsdom), not hand-rolled
 * stubs -- the same file this repo actually serves, unmodified for testing.
 */
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const INDEX_HTML = path.join(__dirname, "..", "..", "index.html");

function loadPage(mockFetch) {
  const html = fs.readFileSync(INDEX_HTML, "utf8");
  const dom = new JSDOM(html, { runScripts: "dangerously", resources: "usable", pretendToBeVisual: true, url: "http://localhost/" });
  if (mockFetch) dom.window.fetch = mockFetch;
  return dom;
}

function preventMockFetch(payloadLog) {
  return async (url, opts) => {
    if (url === "/api/v1/heart-age/calculate") {
      if (payloadLog) payloadLog.push(JSON.parse(opts.body));
      return {
        ok: true,
        json: async () => ({
          chronological_age_years: 60, risk_10yr_percent: 5.3, risk_10yr_unavailable_reason: null,
          risk_30yr_percent: null, risk_30yr_unavailable_reason: "30-Year CVD Risk: Not available for this age range (supported: 30-59).",
          risk_age_years: 63.7, risk_age_boundary_label: null, risk_age_gap_years: 3.7,
          reference_framework: "AHA PREVENT (base equations, Total CVD outcome)",
          disclaimer: "Risk Age is an evidence-based risk communication metric derived from the PREVENT equations. It is not a direct measurement of biological cardiac aging.",
          affiliation_note: "Cardio MIRAI is not affiliated with or endorsed by the American Heart Association.",
        }),
      };
    }
    return { ok: false, json: async () => ({}) };
  };
}

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

test("no duplicate Heart Age input form remains", async () => {
  const dom = loadPage();
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  for (const id of ["haAge", "haSex", "haTC", "haHDL", "haSBP", "haEGFR", "haBPMed", "haStatin", "haDM", "haSmoke", "calcHeartAgeBtn"]) {
    assert.strictEqual(document.getElementById(id), null, `${id} should not exist -- duplicate form must be fully removed`);
  }
});

test("section renamed to Cardio MIRAI Patient Assessment", async () => {
  const dom = loadPage();
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  assert.strictEqual(document.querySelector("#screening h2").textContent, "Cardio MIRAI Patient Assessment");
});

test("age/sex/SBP entered once are automatically reused by PREVENT (no re-entry)", async () => {
  const payloadLog = [];
  const dom = loadPage(preventMockFetch(payloadLog));
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  document.getElementById("age").value = 55;
  document.querySelector('input[name="sex"][value="male"]').checked = true;
  document.getElementById("sbp").value = 145;
  document.getElementById("calculateBtn").dispatchEvent(new dom.window.Event("click"));
  await new Promise(r => setTimeout(r, 250));
  assert.strictEqual(payloadLog.length, 1);
  assert.strictEqual(payloadLog[0].age_years, 55);
  assert.strictEqual(payloadLog[0].sex, "male");
  assert.strictEqual(payloadLog[0].sbp_mmhg, 145);
});

test("diabetes and smoking entered once are automatically reused by PREVENT", async () => {
  const payloadLog = [];
  const dom = loadPage(preventMockFetch(payloadLog));
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  document.querySelector('input[name="diabetes"][value="yes"]').checked = true;
  document.querySelector('input[name="smoking"][value="current"]').checked = true;
  document.getElementById("calculateBtn").dispatchEvent(new dom.window.Event("click"));
  await new Promise(r => setTimeout(r, 250));
  assert.strictEqual(payloadLog[0].has_diabetes, true);
  assert.strictEqual(payloadLog[0].current_smoker, true);
});

test("missing PREVENT labs shows Pending with exact missing-field names, no wasted API call", async () => {
  let fetchCalled = false;
  const dom = loadPage(async () => { fetchCalled = true; return { ok: false, json: async () => ({}) }; });
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  document.getElementById("totalChol").value = "";
  document.getElementById("egfr").value = "";
  document.getElementById("calculateBtn").dispatchEvent(new dom.window.Event("click"));
  await new Promise(r => setTimeout(r, 200));
  const body = document.getElementById("preventRiskBody").innerHTML;
  assert.ok(body.includes("Pending"));
  assert.ok(body.includes("Total cholesterol"));
  assert.ok(body.includes("eGFR"));
  assert.ok(!body.includes("HDL-C"), "HDL-C was NOT cleared and should not be listed as missing");
  assert.strictEqual(fetchCalled, false, "should not call the API when required fields are missing");
});

test("adding the missing labs makes PREVENT calculable without re-entering other fields", async () => {
  const payloadLog = [];
  const dom = loadPage(preventMockFetch(payloadLog));
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  document.getElementById("totalChol").value = "";
  document.getElementById("calculateBtn").dispatchEvent(new dom.window.Event("click"));
  await new Promise(r => setTimeout(r, 200));
  assert.strictEqual(payloadLog.length, 0, "should be Pending, not calculated, with TC missing");
  document.getElementById("totalChol").value = 210; // now provide the missing value
  document.getElementById("calculateBtn").dispatchEvent(new dom.window.Event("click"));
  await new Promise(r => setTimeout(r, 200));
  assert.strictEqual(payloadLog.length, 1);
  assert.strictEqual(payloadLog[0].total_chol_mgdl, 210);
  assert.strictEqual(payloadLog[0].age_years, 60, "age (never re-entered) still carried through correctly");
});

test("Cardiovascular Profile module keeps working when PREVENT labs are missing (module independence)", async () => {
  const dom = loadPage(async () => ({ ok: false, json: async () => ({}) }));
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  document.getElementById("totalChol").value = "";
  document.getElementById("calculateBtn").dispatchEvent(new dom.window.Event("click"));
  await new Promise(r => setTimeout(r, 200));
  assert.ok(document.getElementById("riskLabel").textContent.length > 0);
  assert.ok(document.querySelectorAll("#factorList li").length > 0);
});

test("Integrated Report generates from Cardiovascular Profile + PREVENT alone, ECG marked unavailable (not negative)", async () => {
  const dom = loadPage(preventMockFetch());
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  document.getElementById("calculateBtn").dispatchEvent(new dom.window.Event("click"));
  await new Promise(r => setTimeout(r, 250));
  document.getElementById("generateIntegratedBtn").dispatchEvent(new dom.window.Event("click"));
  const report = document.getElementById("integratedReport").innerHTML;
  assert.ok(report.includes("Cardiovascular Profile"));
  assert.ok(report.includes("5.3%"), "PREVENT result included in the report");
  assert.ok(report.includes("Unavailable -- upload and analyze an ECG"));
  assert.ok(!report.includes("Please upload an ECG and run the ECG Analyzer first"), "old hard-block message must be gone");
});

test("Integrated Report uses canonical current_af_evidence when present, not the legacy score", async () => {
  const dom = loadPage();
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  dom.window.eval(`
    latestEcgResult = {
      inputType: "Digital WFDB", rhythm: "sinus arrhythmia",
      atrialHealth: { current_af_evidence: { category: "intermediate", confidence: 0.4 } },
      atrialRemodelingScore: 21.5, afDetectionScore: 49.0, afProbability: 49.0,
      signalQuality: 82, qualityText: "Good", confidenceScore: 70, morphologyFeatures: [],
    };
  `);
  document.getElementById("generateIntegratedBtn").dispatchEvent(new dom.window.Event("click"));
  const report = document.getElementById("integratedReport").innerHTML;
  assert.ok(report.includes("Current AF Evidence: INTERMEDIATE"));
  assert.ok(report.includes("Legacy Atrial-Abnormality Research Score"));
  assert.ok(!report.includes("Rhythm-based AF likelihood (legacy)"), "canonical field must take precedence when present");
});

test("Integrated Report falls back to legacy fields when atrialHealth is absent (simulated/demo ECG path)", async () => {
  const dom = loadPage(preventMockFetch());
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  document.getElementById("calculateBtn").dispatchEvent(new dom.window.Event("click"));
  await new Promise(r => setTimeout(r, 250));
  dom.window.eval(`
    latestEcgResult = {
      inputType: "Image ECG", rhythm: "sinus rhythm",
      atrialRemodelingScore: 30.0, afDetectionScore: 25.0, afProbability: 25.0,
      signalQuality: 75, qualityText: "Acceptable", confidenceScore: 60, morphologyFeatures: [],
    };
  `);
  document.getElementById("generateIntegratedBtn").dispatchEvent(new dom.window.Event("click"));
  const report = document.getElementById("integratedReport").innerHTML;
  assert.ok(report.includes("Rhythm-based AF likelihood (legacy)"), "must fall back when atrialHealth is genuinely absent");
});

test("Cardio MIRAI AI Heart Age always shows placeholder wording, never a number", async () => {
  const dom = loadPage(preventMockFetch());
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  document.getElementById("calculateBtn").dispatchEvent(new dom.window.Event("click"));
  await new Promise(r => setTimeout(r, 250));
  document.getElementById("generateIntegratedBtn").dispatchEvent(new dom.window.Event("click"));
  const report = document.getElementById("integratedReport").innerHTML;
  assert.ok(report.includes("Research model under development"));
  assert.ok(report.includes("No AI Heart Age number is generated yet"));
});

test("Cardiovascular Profile does not prominently show a bare XX/100 as the headline result", async () => {
  const dom = loadPage(preventMockFetch());
  const { document } = dom.window;
  await new Promise(r => setTimeout(r, 200));
  document.getElementById("calculateBtn").dispatchEvent(new dom.window.Event("click"));
  await new Promise(r => setTimeout(r, 250));
  // The score must exist (preserved internally) but only inside a collapsed <details>, not as the panel's own title/headline.
  const scoreEl = document.getElementById("scoreValue");
  assert.ok(scoreEl, "internal score must still be preserved, not deleted");
  const details = scoreEl.closest("details");
  assert.ok(details, "the numeric score must be inside a collapsed <details>, not the primary headline");
  const panelTitle = document.querySelector(".result-stack .panel-title strong").textContent;
  assert.strictEqual(panelTitle, "Cardiovascular Profile");
});

(async () => {
  let passed = 0, failed = 0;
  for (const t of tests) {
    try {
      await t.fn();
      console.log(`PASS: ${t.name}`);
      passed++;
    } catch (e) {
      console.log(`FAIL: ${t.name}\n  ${e.message}`);
      failed++;
    }
  }
  console.log(`\n${passed} passed, ${failed} failed, ${tests.length} total`);
  process.exit(failed > 0 ? 1 : 0);
})();
