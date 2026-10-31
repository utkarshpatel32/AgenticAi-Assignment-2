"""Run the isolated assignment evaluation and export CSV/JSON/Markdown artifacts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from evaluation.runner import run_evaluation


def main() -> None:
    report = run_evaluation()
    eval_dir = ROOT / "evaluation"
    eval_dir.mkdir(exist_ok=True)
    rows = pd.DataFrame(report["rows"])
    rows.to_csv(eval_dir / "final_results.csv", index=False)
    pd.DataFrame(report["comparison"]).to_csv(eval_dir / "assignment_comparison.csv", index=False)
    (eval_dir / "sample_audit_records.json").write_text(json.dumps(report.get("sample_audit_records", []), ensure_ascii=False, indent=2), encoding="utf-8")
    (eval_dir / "sample_trace_records.json").write_text(json.dumps(report.get("sample_trace_records", []), ensure_ascii=False, indent=2), encoding="utf-8")
    summary = report["summary"]
    comparison = pd.DataFrame(report["comparison"])
    markdown = [
        "# Assignment 2 Evaluation Report",
        "",
        "## Execution summary",
        "",
        f"- Assignment 1 common task baseline: **{summary['assignment1_passed']}/{summary['assignment1_total']}**.",
        f"- Assignment 2 test suite: **{summary['assignment2_passed']}/{summary['assignment2_total']} ({summary['assignment2_accuracy']:.0%})**.",
        f"- Assignment 1 mean local latency: **{summary['assignment1_mean_latency_ms']} ms**.",
        f"- Assignment 2 mean local latency: **{summary['assignment2_mean_latency_ms']} ms**.",
        f"- {report['note']}",
        "",
        "## Assignment 1 vs Assignment 2",
        "",
        comparison.to_markdown(index=False),
        "",
        "## Test results",
        "",
        rows[["test_id", "version", "expected_behavior", "passed", "latency_ms", "input_tokens", "output_tokens", "estimated_text_input_tokens", "estimated_text_output_tokens", "result"]].to_markdown(index=False),
        "",
        "## Interpretation and limitations",
        "",
        "This is a small deterministic offline functional test suite, not a statistically representative or human-reviewed accuracy benchmark. The Assignment 1 comparison reruns the supplied Assignment 1 agent for two common, non-sensitive tasks; the qualitative baseline statements for authentication, approval and audit controls come from inspection of the supplied Assignment 1 code/UI. Latencies depend on the local machine. Offline runs do not return API token counts. The `estimated_text_*` columns use a rough character-based estimate and are not exact or billed model-token counts; exact API usage appears in chat traces when Groq returns usage metadata.",
        "",
        "All records in this report are fictional demo data. The evaluation runs in a temporary SQLite database and does not alter the default app database.",
    ]
    (eval_dir / "ASSIGNMENT2_EVALUATION_REPORT.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote evaluation artifacts under: {eval_dir}")


if __name__ == "__main__":
    main()
