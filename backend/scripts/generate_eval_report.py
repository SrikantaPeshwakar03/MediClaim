"""
Eval Report Generator

Runs all 12 test cases from test_cases.json through the full claims-processing
pipeline (deterministically, using the test harness mocks) and writes a markdown
evaluation report with, for each case:
  - the decision the system produced
  - the full execution trace
  - whether it matched the expected outcome (and why, if not)

Usage:
    python backend/scripts/generate_eval_report.py
Writes:
    EVAL_REPORT.md  (project root)
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

# Make the backend package and tests importable
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "tests"))

from test_all_cases import create_mock_services_for_test, TEST_CASES_DATA  # noqa: E402
from app.models import ClaimCategory, create_initial_state  # noqa: E402
from app.agents.orchestrator import ClaimsOrchestrator  # noqa: E402


def _run_case(test_case: dict) -> dict:
    """Run a single test case through the pipeline and return the final state."""
    inp = test_case["input"]
    mocks = create_mock_services_for_test(test_case)
    structured_by_index = mocks["structured_by_index"]

    def fake_extract_structured(self, raw_text, doc_type):
        import re
        m = re.search(r"doc(\d+)", raw_text or "")
        if m and int(m.group(1)) < len(structured_by_index):
            return structured_by_index[int(m.group(1))]
        return {}

    def normalized_history():
        history = []
        for c in inp.get("claims_history", []):
            item = dict(c)
            raw = item.get("date") or item.get("treatment_date")
            if isinstance(raw, str):
                try:
                    item["treatment_date"] = date.fromisoformat(raw)
                except ValueError:
                    item["treatment_date"] = None
            history.append(item)
        return history

    with patch("app.agents.document_verifier.get_policy_engine", return_value=mocks["policy_engine"]), \
         patch("app.agents.document_verifier.get_ocr_service", return_value=mocks["ocr_service"]), \
         patch("app.agents.document_verifier.get_llm_service", return_value=mocks["llm_service"]), \
         patch("app.agents.ocr_extractor.get_ocr_service", return_value=mocks["ocr_service"]), \
         patch("app.agents.ocr_extractor.get_llm_service", return_value=mocks["llm_service"]), \
         patch("app.agents.ocr_extractor.OCRExtractorAgent._extract_structured_fields", fake_extract_structured), \
         patch("app.agents.policy_validator.get_policy_engine", return_value=mocks["policy_engine"]), \
         patch("app.agents.fraud_detector.FraudDetectorAgent._get_claim_history", return_value=normalized_history()):
        orchestrator = ClaimsOrchestrator()
        state = create_initial_state(
            claim_id=f"EVAL_{test_case['case_id']}",
            member_id=inp.get("member_id", "EMP001"),
            policy_id=inp.get("policy_id", "PLUM_GHI_2024"),
            claim_category=ClaimCategory[inp.get("claim_category", "CONSULTATION")],
            treatment_date=date.fromisoformat(inp.get("treatment_date", "2024-11-01")),
            claimed_amount=inp.get("claimed_amount", 1500),
            document_file_paths=[f"doc{i}.jpg" for i in range(len(inp.get("documents", [])))],
            document_metadata=[{"file_name": f"doc{i}.jpg"} for i in range(len(inp.get("documents", [])))],
            hospital_name=inp.get("hospital_name"),
            simulate_component_failure=inp.get("simulate_component_failure", False),
        )
        return orchestrator.process_claim(state)


def _evaluate(test_case: dict, final_state: dict) -> tuple[bool, str]:
    """Compare the produced outcome against the expected outcome."""
    expected = test_case["expected"]
    exp_decision = expected.get("decision")

    decision_obj = final_state.get("final_decision")
    actual_decision = final_state.get("decision")
    actual_decision_val = actual_decision.value if actual_decision else None

    # Cases that must stop before a decision (document problems)
    if exp_decision is None:
        if final_state.get("stop_processing") and actual_decision_val is None:
            return True, "Pipeline stopped before a decision, as required."
        return False, (
            f"Expected the pipeline to stop with no decision, but got "
            f"decision={actual_decision_val}, stop_processing={final_state.get('stop_processing')}."
        )

    # Decision-type match
    if actual_decision_val != exp_decision:
        return False, f"Expected decision {exp_decision}, got {actual_decision_val}."

    notes = []
    # Approved amount check when specified
    if "approved_amount" in expected and decision_obj is not None:
        exp_amt = expected["approved_amount"]
        act_amt = decision_obj.approved_amount
        if abs((act_amt or 0) - exp_amt) > 0.5:
            return False, f"Expected approved amount ₹{exp_amt}, got ₹{act_amt}."
        notes.append(f"approved amount ₹{act_amt:,.2f} matches")

    # Rejection reasons check when specified
    if "rejection_reasons" in expected and decision_obj is not None:
        exp_reasons = set(expected["rejection_reasons"])
        act_reasons = {r.value for r in decision_obj.rejection_reasons}
        if not exp_reasons.issubset(act_reasons):
            return False, f"Expected rejection reasons {exp_reasons}, got {act_reasons}."
        notes.append(f"rejection reasons {sorted(act_reasons)} match")

    return True, "Decision matches expected outcome" + (f" ({'; '.join(notes)})." if notes else ".")


def _fmt_trace(final_state: dict) -> str:
    lines = []
    for entry in final_state.get("trace", []):
        agent = entry.get("agent", "?")
        status = entry.get("status", "?")
        out = entry.get("output", {})
        lines.append(f"- **{agent}** — `{status}`")
        if isinstance(out, dict):
            for k in ("verification_passed", "all_checks_passed", "eligible_amount",
                      "fraud_score", "num_signals", "decision", "approved_amount",
                      "confidence_score", "decision_message"):
                if k in out and out[k] is not None:
                    lines.append(f"    - {k}: {out[k]}")
        if entry.get("error"):
            lines.append(f"    - error: {entry['error']}")
    return "\n".join(lines) if lines else "_(no trace)_"


def main():
    cases = TEST_CASES_DATA["test_cases"]
    results = []
    for tc in cases:
        final_state = _run_case(tc)
        matched, explanation = _evaluate(tc, final_state)
        results.append((tc, final_state, matched, explanation))

    passed = sum(1 for *_, m, _ in [(r[0], r[1], r[2], r[3]) for r in results] if m)
    total = len(results)

    out = []
    out.append("# MediClaim — Evaluation Report")
    out.append("")
    out.append(f"_Generated: {datetime.utcnow().isoformat()}Z_")
    out.append("")
    out.append(f"**Result: {passed}/{total} test cases matched the expected outcome.**")
    out.append("")
    out.append("This report runs every case from `test_cases.json` through the full "
               "5-agent pipeline (DocumentVerifier → OCRExtractor → PolicyValidator → "
               "FraudDetector → DecisionMaker). External services (OCR/LLM/Supabase) are "
               "stubbed deterministically so the run is reproducible; all decision and "
               "policy logic is the real production code.")
    out.append("")

    # Summary table
    out.append("## Summary")
    out.append("")
    out.append("| Case | Name | Expected | Actual | Match |")
    out.append("|------|------|----------|--------|-------|")
    for tc, fs, matched, _ in results:
        exp = tc["expected"].get("decision") or "STOP (no decision)"
        dec = fs.get("decision")
        actual = dec.value if dec else ("STOP (no decision)" if fs.get("stop_processing") else "—")
        out.append(f"| {tc['case_id']} | {tc['case_name']} | {exp} | {actual} | {'✅' if matched else '❌'} |")
    out.append("")

    # Per-case detail
    out.append("## Case Details")
    out.append("")
    for tc, fs, matched, explanation in results:
        dec = fs.get("final_decision")
        out.append(f"### {tc['case_id']} — {tc['case_name']}")
        out.append("")
        out.append(f"**Status: {'PASS ✅' if matched else 'FAIL ❌'}** — {explanation}")
        out.append("")
        out.append(f"- Expected: `{tc['expected'].get('decision') or 'no decision (stop early)'}`")
        if dec is not None:
            out.append(f"- Decision: `{dec.decision.value}`")
            out.append(f"- Approved amount: ₹{(dec.approved_amount or 0):,.2f}")
            out.append(f"- Confidence: {dec.confidence_score:.2f}")
            if dec.rejection_reasons:
                out.append(f"- Rejection reasons: {[r.value for r in dec.rejection_reasons]}")
            if dec.requires_manual_review:
                out.append(f"- Manual review: {dec.manual_review_reason}")
            out.append(f"- Message: {dec.decision_message}")
        else:
            vr = fs.get("verification_result")
            out.append("- Decision: _none (pipeline stopped at verification)_")
            if vr and vr.errors:
                out.append("- Verification errors:")
                for e in vr.errors:
                    out.append(f"    - {e}")
        out.append("")
        out.append("**Execution trace:**")
        out.append("")
        out.append(_fmt_trace(fs))
        out.append("")
        if fs.get("components_failed"):
            out.append(f"_Components failed (graceful degradation): {sorted(set(fs['components_failed']))}_")
            out.append("")

    report_path = PROJECT_ROOT / "EVAL_REPORT.md"
    report_path.write_text("\n".join(out))
    print(f"Wrote {report_path} ({passed}/{total} matched)")


if __name__ == "__main__":
    main()
