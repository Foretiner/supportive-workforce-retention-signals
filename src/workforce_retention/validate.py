from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def rows(root: Path, filename: str) -> list[dict[str, str]]:
    with (root / filename).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate(root: Path) -> dict:
    errors: list[str] = []
    employees = rows(root, "employees.csv")
    roles = rows(root, "roles.csv")
    teams = rows(root, "teams.csv")
    emp_ids = [r["employee_id"] for r in employees]
    role_ids, team_ids = {r["role_id"] for r in roles}, {r["team_id"] for r in teams}
    if len(emp_ids) != len(set(emp_ids)): errors.append("employees.employee_id is not unique")
    if len(role_ids) != len(roles): errors.append("roles.role_id is not unique")
    if len(team_ids) != len(teams): errors.append("teams.team_id is not unique")
    emp_set = set(emp_ids)
    for r in employees:
        if r["initial_role_id"] not in role_ids: errors.append(f"unknown role for {r['employee_id']}")
        if r["initial_team_id"] not in team_ids: errors.append(f"unknown team for {r['employee_id']}")
    simple_keys = {"tenure_snapshots.csv": "tenure_snapshot_id", "engagement_surveys.csv": "survey_id",
                   "workload_snapshots.csv": "workload_snapshot_id", "compensation_bands.csv": "compensation_record_id",
                   "promotion_history.csv": "promotion_id", "attrition_outcomes.csv": "outcome_id", "interventions.csv": "intervention_id"}
    table_counts = {}
    for filename, key in simple_keys.items():
        data = rows(root, filename); table_counts[filename] = len(data)
        ids = [r[key] for r in data]
        if len(ids) != len(set(ids)): errors.append(f"{filename}.{key} is not unique")
        for r in data:
            if r["employee_id"] not in emp_set: errors.append(f"{filename} has invalid employee FK {r['employee_id']}")
            for col in ("role_id", "from_role_id", "to_role_id"):
                if col in r and r[col] and r[col] not in role_ids: errors.append(f"{filename} has invalid role FK {r[col]}")
            if "team_id" in r and r["team_id"] not in team_ids: errors.append(f"{filename} has invalid team FK {r['team_id']}")
    surveys = rows(root, "engagement_surveys.csv")
    for s in surveys:
        if s["response_status"] not in {"Responded", "Missing"}: errors.append("invalid survey response_status")
        for c in ("engagement_score", "belonging_score", "growth_score"):
            if s["response_status"] == "Missing" and s[c] != "": errors.append("missing survey score should remain null")
            if s["response_status"] == "Responded" and not 1 <= float(s[c]) <= 5: errors.append("survey score outside 1-5")
    for w in rows(root, "workload_snapshots.csv"):
        if float(w["weekly_hours"]) < 0 or float(w["weekly_hours"]) > 70: errors.append("weekly_hours outside 0-70")
        if round(max(0, float(w["weekly_hours"]) - 40), 1) != float(w["overtime_hours"]): errors.append("overtime arithmetic mismatch")
    for o in rows(root, "attrition_outcomes.csv"):
        has_term = bool(o["termination_date"])
        if int(o["voluntary_attrition"]) != int(has_term): errors.append(f"outcome/date mismatch for {o['employee_id']}")
        if has_term and not o["horizon_start"] <= o["termination_date"] <= o["horizon_end"]: errors.append("termination outside outcome horizon")
    # Explicitly verify all features used by analysis are dated on/before the cutoff.
    for filename, date_col in (("engagement_surveys.csv", "survey_date"), ("workload_snapshots.csv", "snapshot_date")):
        for r in rows(root, filename):
            if r[date_col] > "2025-12-31": errors.append(f"future feature date in {filename}: {r[date_col]}")
    report = {"status": "PASS" if not errors else "FAIL", "employee_count": len(employees), "tables_checked": len(simple_keys) + 3,
              "row_counts": table_counts, "error_count": len(errors), "errors": errors}
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Validate generated workforce data")
    p.add_argument("--data", type=Path, default=Path("data/generated")); args = p.parse_args()
    report = validate(args.data)
    print(json.dumps(report, indent=2))
    if report["errors"]: raise SystemExit(1)


if __name__ == "__main__": main()
