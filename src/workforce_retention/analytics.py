from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def analyze(data_dir: Path, output: Path) -> dict:
    """Create aggregate, interpretable support priorities from pre-outcome signals."""
    employees = read(data_dir / "employees.csv")
    surveys = read(data_dir / "engagement_surveys.csv")
    workloads = read(data_dir / "workload_snapshots.csv")
    outcomes = read(data_dir / "attrition_outcomes.csv")
    survey_by_emp: dict[str, list[float]] = defaultdict(list)
    survey_missing = defaultdict(int)
    for row in surveys:
        if row["response_status"] == "Responded" and row["engagement_score"]:
            survey_by_emp[row["employee_id"]].append(float(row["engagement_score"]))
        else:
            survey_missing[row["employee_id"]] += 1
    loads: dict[str, list[float]] = defaultdict(list)
    for row in workloads:
        if row["snapshot_date"] <= "2025-12-31":
            loads[row["employee_id"]].append(float(row["weekly_hours"]))
    outcome_by_emp = {r["employee_id"]: int(r["voluntary_attrition"]) for r in outcomes}

    decisions = []
    for emp in employees:
        eid = emp["employee_id"]
        scores, hours = survey_by_emp[eid], loads[eid]
        avg_engagement = mean(scores) if scores else None
        avg_hours = mean(hours) if hours else None
        # Clear rules: low engagement <=2.8 (if observed) OR persistent load >50h.
        reasons = []
        if avg_engagement is not None and avg_engagement <= 2.8:
            reasons.append("low_observed_engagement")
        if avg_hours is not None and avg_hours > 50:
            reasons.append("sustained_high_average_hours")
        priority = "Offer supportive check-in" if reasons else "Routine support available"
        decisions.append(dict(employee_id=eid, prediction_cutoff="2025-12-31",
                              avg_observed_engagement=round(avg_engagement, 2) if avg_engagement is not None else "",
                              missing_survey_count=survey_missing[eid], avg_weekly_hours=round(avg_hours, 2) if avg_hours is not None else "",
                              reason_codes="|".join(reasons), suggested_support=priority,
                              disclaimer="Supportive signal only; no employment decision; human review required"))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(decisions[0]) if decisions else [])
        writer.writeheader(); writer.writerows(decisions)

    n = len(outcomes)
    positives = sum(outcome_by_emp.values())
    flagged = {d["employee_id"] for d in decisions if d["reason_codes"]}
    true_positive = sum(1 for eid in flagged if outcome_by_emp.get(eid) == 1)
    actual_positive = {eid for eid, label in outcome_by_emp.items() if label}
    metrics = {
        "population": n,
        "voluntary_attrition_rate": round(positives / n, 4) if n else 0,
        "support_checkin_suggestions": len(flagged),
        "suggestion_rate": round(len(flagged) / n, 4) if n else 0,
        "precision_against_simulated_labels": round(true_positive / len(flagged), 4) if flagged else 0,
        "recall_against_simulated_labels": round(true_positive / len(actual_positive), 4) if actual_positive else 0,
        "evaluation_note": "Descriptive retrospective metrics only. For model evaluation use time-based holdout; never interpret as causal or employment decision.",
        "decision_rules": ["average observed engagement <= 2.8/5", "average pre-cutoff weekly hours > 50"],
    }
    (output.parent / "evaluation_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    p = argparse.ArgumentParser(description="Create explainable supportive retention signals")
    p.add_argument("--data", type=Path, default=Path("data/generated"))
    p.add_argument("--out", type=Path, default=Path("data/analysis/support_recommendations.csv"))
    args = p.parse_args()
    print(json.dumps(analyze(args.data, args.out), indent=2))


if __name__ == "__main__":
    main()
