"""Run a fresh 60-ticket evaluation against the LangGraph agent.

Run from the project root:
    python run_pw_langgraph_eval_60_v1.py

This invokes the actual LangGraph workflow and may make paid API calls.
"""
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

from pw_langgraph_evalset_60_v1 import TEST_CASES
from ticket_agent_graph import process_ticket_with_graph

LABELS = ["academic_doubt", "technical", "payment", "batch_access", "refund", "fee_structure", "human_review"]
RESULTS = Path("pw_langgraph_eval_results_60_v1.csv")
CATEGORY_METRICS = Path("pw_langgraph_category_metrics_60_v1.csv")
SUMMARY = Path("pw_langgraph_eval_summary_60_v1.json")


def main():
    rows = []
    total = len(TEST_CASES)
    print(f"Running LangGraph evaluation on {total} tickets.")
    print("This can take time and may incur OpenAI API costs.\n")

    for i, case in enumerate(TEST_CASES, start=1):
        try:
            result = process_ticket_with_graph(case["ticket"])
            predicted = set(result.get("categories") or [])
            expected = set(case["expected_categories"])
            pred_review = bool(result.get("needs_human_review", False))
            expected_review = bool(case["expected_human_review"])
            expected_risk = case.get("expected_risk")
            predicted_risk = result.get("risk_level")
            rows.append({
                "id": case["id"], "ticket": case["ticket"],
                "expected_categories": "|".join(sorted(expected)),
                "predicted_categories": "|".join(sorted(predicted)),
                "category_exact_match": expected == predicted,
                "expected_human_review": expected_review,
                "predicted_human_review": pred_review,
                "human_review_correct": expected_review == pred_review,
                "expected_risk": expected_risk or "",
                "predicted_risk": predicted_risk or "",
                "risk_scored": expected_risk is not None,
                "risk_correct": expected_risk is not None and str(expected_risk).lower() == str(predicted_risk).lower(),
                "action": result.get("action", ""),
                "reply_generated": bool(result.get("draft_reply")),
                "sources_count": len(result.get("sources") or []),
                "sources": "|".join(map(str, result.get("sources") or [])),
                "error": "",
            })
            print(f"[{i:02d}/{total}] {case['id']} categories={sorted(predicted)}")
        except Exception as exc:
            rows.append({
                "id": case["id"], "ticket": case["ticket"],
                "expected_categories": "|".join(sorted(case["expected_categories"])),
                "predicted_categories": "", "category_exact_match": False,
                "expected_human_review": bool(case["expected_human_review"]),
                "predicted_human_review": False, "human_review_correct": False,
                "expected_risk": case.get("expected_risk") or "", "predicted_risk": "",
                "risk_scored": case.get("expected_risk") is not None, "risk_correct": False,
                "action": "", "reply_generated": False, "sources_count": 0,
                "sources": "", "error": repr(exc),
            })
            print(f"[{i:02d}/{total}] {case['id']} ERROR: {exc}")

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS, index=False, encoding="utf-8-sig")

    y_true, y_pred = [], []
    for case, row in zip(TEST_CASES, rows):
        expected = set(case["expected_categories"])
        predicted = set(filter(None, row["predicted_categories"].split("|")))
        y_true.append([int(label in expected) for label in LABELS])
        y_pred.append([int(label in predicted) for label in LABELS])

    p, r, f1, support = precision_recall_fscore_support(y_true, y_pred, average=None, zero_division=0)
    category_rows = []
    for j, label in enumerate(LABELS):
        tp = sum(yt[j] == 1 and yp[j] == 1 for yt, yp in zip(y_true, y_pred))
        fp = sum(yt[j] == 0 and yp[j] == 1 for yt, yp in zip(y_true, y_pred))
        fn = sum(yt[j] == 1 and yp[j] == 0 for yt, yp in zip(y_true, y_pred))
        tn = len(rows) - tp - fp - fn
        category_rows.append({
            "category": label, "precision": round(float(p[j]), 4),
            "recall": round(float(r[j]), 4), "f1": round(float(f1[j]), 4),
            "support": int(support[j]), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        })
    pd.DataFrame(category_rows).to_csv(CATEGORY_METRICS, index=False, encoding="utf-8-sig")

    macro_p, macro_r, macro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    risk_rows = [row for row in rows if row["risk_scored"]]
    summary = {
        "agent": "LangGraph: ticket_agent_graph.process_ticket_with_graph",
        "total_cases": total,
        "processed_without_error": sum(not row["error"] for row in rows),
        "error_count": sum(bool(row["error"]) for row in rows),
        "category_exact_match_accuracy": round(float(df["category_exact_match"].mean()), 4),
        "macro_precision": round(float(macro_p), 4),
        "macro_recall": round(float(macro_r), 4),
        "macro_f1": round(float(macro_f1), 4),
        "human_review_accuracy": round(float(df["human_review_correct"].mean()), 4),
        "risk_scored_cases": len(risk_rows),
        "risk_accuracy_on_scored_cases": round(sum(row["risk_correct"] for row in risk_rows) / len(risk_rows), 4) if risk_rows else None,
        "reply_generated_count": int(df["reply_generated"].sum()),
        "cases_with_sources_count": int((df["sources_count"] > 0).sum()),
        "note": "Metrics describe this curated 60-ticket set only; they do not guarantee real-world performance.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n===== EVALUATION SUMMARY =====")
    print(json.dumps(summary, indent=2))
    print("\n===== CATEGORY METRICS =====")
    print(pd.DataFrame(category_rows).to_string(index=False))
    print(f"\nSaved: {RESULTS}, {CATEGORY_METRICS}, {SUMMARY}")


if __name__ == "__main__":
    main()
