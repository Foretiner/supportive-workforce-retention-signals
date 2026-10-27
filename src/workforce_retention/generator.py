from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

SEED_DEFAULT = 20261022
START = date(2024, 1, 1)
MONTHS = 24

ROLES = [
    ("ROLE-001", "Analyst", "Individual Contributor", 1),
    ("ROLE-002", "Senior Analyst", "Individual Contributor", 2),
    ("ROLE-003", "Manager", "People Manager", 3),
    ("ROLE-004", "Senior Manager", "People Manager", 4),
    ("ROLE-005", "Engineer", "Individual Contributor", 1),
    ("ROLE-006", "Senior Engineer", "Individual Contributor", 2),
    ("ROLE-007", "Operations Specialist", "Individual Contributor", 1),
    ("ROLE-008", "Product Lead", "People Manager", 3),
]
TEAMS = [("TEAM-001", "Data"), ("TEAM-002", "Engineering"), ("TEAM-003", "Operations"), ("TEAM-004", "Product")]
SURVEY_FIELDS = ["survey_id", "employee_id", "survey_date", "engagement_score", "belonging_score", "growth_score", "response_status"]


def month_date(month_index: int) -> date:
    year = START.year + (START.month - 1 + month_index) // 12
    month = (START.month - 1 + month_index) % 12 + 1
    return date(year, month, 1)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def generate(out: Path, employees_count: int = 200, seed: int = SEED_DEFAULT) -> dict[str, Any]:
    """Generate valid baseline tables plus isolated labelled exception records."""
    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    roles = [dict(role_id=i, role_name=n, job_family=f, level=l) for i, n, f, l in ROLES]
    teams = [dict(team_id=i, team_name=n) for i, n in TEAMS]
    employees, tenure, workload, surveys, compensation, promotions = [], [], [], [], [], []
    outcomes, interventions = [], []
    survey_counter = intervention_counter = 0
    voluntary_count = 0

    for n in range(1, employees_count + 1):
        emp = f"EMP-{n:06d}"
        hire_offset = rng.randrange(0, 84)  # months before observation window
        hire_year = 2017 + hire_offset // 12
        hire_month = hire_offset % 12 + 1
        hire_date = date(hire_year, hire_month, 1)
        role = rng.choice(roles)
        team = rng.choice(teams)
        baseline_role, baseline_team = role["role_id"], team["team_id"]
        employees.append(dict(employee_id=emp, hire_date=hire_date.isoformat(), initial_role_id=baseline_role,
                              initial_team_id=baseline_team, employment_type="Full-time", lifecycle_state="Active at start",
                              record_source="synthetic_generator"))
        tenure_band = "<1 year" if (START - hire_date).days < 365 else ("1-3 years" if (START - hire_date).days < 1095 else "3+ years")
        tenure.append(dict(tenure_snapshot_id=f"TEN-{emp}-2026Q1", employee_id=emp, as_of_date="2026-01-01",
                           tenure_months=max(0, (START.year - hire_date.year) * 12 + START.month - hire_date.month), tenure_band=tenure_band))

        latent_risk = rng.random()
        exits_in_horizon = latent_risk >= 0.90
        exit_month = rng.randrange(1, 13) if exits_in_horizon else None
        if exits_in_horizon:
            voluntary_count += 1
        score = round(min(100, max(0, 75 + rng.gauss(0, 10) - latent_risk * 25)), 1)
        base_load = max(20, min(65, round(rng.gauss(35 + latent_risk * 20, 7))))
        current_role, current_team = baseline_role, baseline_team
        promoted = False
        current_salary = rng.randrange(55000, 105001, 1000)
        for m in range(MONTHS):
            d = month_date(m)
            # Intentional internal transfers; state is recorded in snapshot history.
            if m in (9, 15) and rng.random() < 0.035:
                current_team = rng.choice([t["team_id"] for t in teams if t["team_id"] != current_team])
            if not promoted and m >= 12 and rng.random() < 0.10:
                old = current_role
                candidates = [r for r in roles if r["level"] == next((x["level"] for x in roles if x["role_id"] == old), 1) + 1]
                if candidates:
                    current_role = rng.choice(candidates)["role_id"]
                    current_salary = int(current_salary * 1.10)
                    promotions.append(dict(promotion_id=f"PROM-{emp}-{d:%Y%m}", employee_id=emp, effective_date=d.isoformat(),
                                           from_role_id=old, to_role_id=current_role, salary_after=current_salary))
                    promoted = True
            # A few benign high workload episodes are intentionally unrelated to attrition.
            benign_peak = (n % 17 == 0 and m in (4, 5)) or rng.random() < 0.015
            hours = round(max(20, min(70, base_load + (22 if benign_peak else 0) + rng.gauss(0, 5))), 1)
            workload.append(dict(workload_snapshot_id=f"LOAD-{emp}-{d:%Y%m}", employee_id=emp, snapshot_date=d.isoformat(),
                                 weekly_hours=hours, overtime_hours=round(max(0, hours - 40), 1), project_count=rng.randint(1, 5),
                                 role_id=current_role, team_id=current_team))
            # Engagement is observed quarterly; missing responses remain null and are not encoded as low scores.
            if m % 3 == 2:
                survey_counter += 1
                missing = rng.random() < 0.13
                surveys.append(dict(survey_id=f"SURV-2026-{survey_counter:06d}", employee_id=emp, survey_date=d.isoformat(),
                                    engagement_score="" if missing else round(max(1, min(5, score / 20 + rng.gauss(0, .35))), 1),
                                    belonging_score="" if missing else round(max(1, min(5, score / 20 + rng.gauss(0, .45))), 1),
                                    growth_score="" if missing else round(max(1, min(5, score / 20 + rng.gauss(0, .5))), 1),
                                    response_status="Missing" if missing else "Responded"))
            if m in (0, 12):
                compensation.append(dict(compensation_record_id=f"COMP-{emp}-{d:%Y%m}", employee_id=emp, effective_date=d.isoformat(),
                                         annual_salary=current_salary, currency="USD", band=f"B{min(8, max(1, current_salary // 15000))}"))
        term = date(2026, exit_month, 1).isoformat() if exit_month is not None else ""
        outcomes.append(dict(outcome_id=f"OUT-{emp}-2026", employee_id=emp, horizon_start="2026-01-01", horizon_end="2026-12-31",
                             voluntary_attrition=int(exit_month is not None), termination_date=term,
                             label_rule="voluntary separation during 2026 horizon; simulated from pre-horizon latent risk"))
        # Simulated intervention is a supportive check-in, not a personnel action.
        if rng.random() < 0.18:
            intervention_counter += 1
            interventions.append(dict(intervention_id=f"INT-2026-{intervention_counter:06d}", employee_id=emp,
                                      created_at="2026-01-15", intervention_type="Supportive check-in", status="Completed",
                                      outcome="Needs follow-up" if latent_risk > .72 else "No follow-up requested",
                                      actor_role="Manager", rationale="Aggregate pre-horizon workload and survey context; human review required"))

    # Curated exceptions live outside canonical source tables and never contaminate model features.
    edge_cases = [
        dict(case_id="EDGE-001", issue_type="future_information_leak", entity="feature_example", record_id="EX-FUTURE-001",
             description="Contains a survey value dated after the prediction cutoff.", expected_decision="Reject feature; enforce event_date <= cutoff_date", ground_truth_label="invalid_feature"),
        dict(case_id="EDGE-002", issue_type="missing_survey_as_negative", entity="feature_example", record_id="EX-MISSING-001",
             description="A missing survey was incorrectly converted to the minimum score.", expected_decision="Preserve null and report missingness", ground_truth_label="invalid_imputation"),
        dict(case_id="EDGE-003", issue_type="outcome_date_label_mismatch", entity="outcome_example", record_id="EX-OUTCOME-001",
             description="Label says no attrition but voluntary termination date is in horizon.", expected_decision="Flag inconsistent outcome for review", ground_truth_label="invalid_outcome"),
        dict(case_id="EDGE-004", issue_type="unexplained_individual_score", entity="decision_example", record_id="EX-SCORE-001",
             description="An individual score is shown without reasons or human review.", expected_decision="Suppress score; require explainable aggregate signal and reviewer", ground_truth_label="unsupported_decision"),
    ]
    feature_examples = [
        dict(example_id="EX-FUTURE-001", employee_id="EMP-000001", prediction_cutoff="2025-12-31", event_date="2026-03-31", feature_name="engagement_score", feature_value=2.1),
        dict(example_id="EX-MISSING-001", employee_id="EMP-000002", prediction_cutoff="2025-12-31", event_date="2025-12-31", feature_name="engagement_score", feature_value=1.0),
    ]
    outcome_examples = [dict(example_id="EX-OUTCOME-001", voluntary_attrition=0, termination_date="2026-06-01", horizon_start="2026-01-01", horizon_end="2026-12-31")]
    decision_examples = [dict(example_id="EX-SCORE-001", individual_score=0.93, explanation="", human_review="No")]

    tables = {"employees.csv": employees, "roles.csv": roles, "teams.csv": teams, "tenure_snapshots.csv": tenure,
              "engagement_surveys.csv": surveys, "workload_snapshots.csv": workload, "compensation_bands.csv": compensation,
              "promotion_history.csv": promotions, "attrition_outcomes.csv": outcomes, "interventions.csv": interventions,
              "ground_truth.csv": edge_cases, "edge_feature_examples.csv": feature_examples,
              "edge_outcome_examples.csv": outcome_examples, "edge_decision_examples.csv": decision_examples}
    for filename, rows in tables.items():
        write_csv(out / filename, rows)
    summary = {"seed": seed, "employees": employees_count, "observation_months": MONTHS,
               "outcomes": len(outcomes), "voluntary_attrition_count": voluntary_count,
               "attrition_rate": round(voluntary_count / employees_count, 4) if employees_count else 0,
               "rows": {name: len(rows) for name, rows in tables.items()}, "files": {}}
    for filename in tables:
        b = (out / filename).read_bytes()
        summary["files"][filename] = hashlib.sha256(b).hexdigest()
    (out / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "source_manifest.json").write_text(json.dumps({"provenance": "Entirely synthetic; no external or personal data used.",
        "generator": "workforce_retention.generator", "seed": seed, "observation_start": START.isoformat(), "observation_months": MONTHS}, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reproducible synthetic workforce retention data")
    parser.add_argument("--employees", type=int, default=200, help="Employee count (default: 200; use 10000 for full volume)")
    parser.add_argument("--seed", type=int, default=SEED_DEFAULT)
    parser.add_argument("--out", type=Path, default=Path("data/generated"))
    args = parser.parse_args()
    if args.employees < 1:
        parser.error("--employees must be >= 1")
    print(json.dumps(generate(args.out, args.employees, args.seed), indent=2))


if __name__ == "__main__":
    main()
