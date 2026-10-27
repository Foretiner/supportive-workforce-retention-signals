# Data dictionary

All data is synthetic. `employee_id` references `employees.employee_id`; role and team references point to their respective master tables. Dates are ISO-8601 calendar dates. Blank CSV cells represent null. IDs are immutable. Snapshot tables are append-only histories; `effective_date` or snapshot date defines when a record applies.

| Entity / file | Primary key | Fields (type; required; allowed values / validation) | Relationships and cardinality |
|---|---|---|---|
| Employee / `employees.csv` | `employee_id` | `EMP-000001` format; `hire_date` date; `initial_role_id`, `initial_team_id` FKs; `employment_type` enum (`Full-time`); `lifecycle_state` string; `record_source` string | Employee 1:N tenure, surveys, workload, compensation, promotions, outcomes, interventions |
| Role / `roles.csv` | `role_id` | ID; `role_name` string unique in catalog; `job_family` string; `level` integer 1–4 | Role 1:N employees (initial), workloads, promotions |
| Team / `teams.csv` | `team_id` | ID; `team_name` unique in catalog | Team 1:N employees (initial), workloads |
| TenureSnapshot / `tenure_snapshots.csv` | `tenure_snapshot_id` | deterministic `TEN-<employee>-2026Q1`; employee FK; `as_of_date`; `tenure_months` integer >=0; `tenure_band` enum `<1 year`, `1-3 years`, `3+ years` | Employee 1:N snapshots; one snapshot per employee in this export |
| EngagementSurvey / `engagement_surveys.csv` | `survey_id` | `SURV-2026-######`; employee FK; `survey_date`; three nullable numeric scores [1,5]; `response_status` enum (`Responded`, `Missing`); Missing requires blank scores | Employee 1:N dated survey events; missingness is explicit, never a negative score |
| WorkloadSnapshot / `workload_snapshots.csv` | `workload_snapshot_id` | deterministic `LOAD-<employee>-YYYYMM`; employee, role, team FKs; monthly snapshot date; `weekly_hours` numeric [20,70]; `overtime_hours=max(0,weekly_hours-40)`; `project_count` integer [1,5] | Employee 1:N monthly snapshots; role/team 1:N snapshots |
| CompensationBand / `compensation_bands.csv` | `compensation_record_id` | deterministic `COMP-<employee>-YYYYMM`; employee FK; `effective_date`; `annual_salary` USD integer >0; `currency` USD; `band` string | Employee 1:N effective-dated compensation records |
| PromotionHistory / `promotion_history.csv` | `promotion_id` | deterministic `PROM-<employee>-YYYYMM`; employee/from-role/to-role FKs; effective date; salary_after USD integer | Employee 1:N promotion events; role 1:N from/to events |
| AttritionOutcome / `attrition_outcomes.csv` | `outcome_id` | `OUT-<employee>-2026`; employee FK; horizon dates; binary `voluntary_attrition`; optional termination date; label rule. Positive iff voluntary termination date is within horizon | Employee 1:1 horizon outcome in this dataset; outcome is future label, never feature |
| Intervention / `interventions.csv` | `intervention_id` | `INT-2026-######`; employee FK; created date; `intervention_type`; status (`Completed`); outcome string; actor role; rationale | Employee 1:N intervention events; lifecycle/status is event history |

## Additional artifacts

`ground_truth.csv` has one row per intentionally modeled exception type, with `case_id` primary key, `issue_type`, entity/record reference, expected decision, and truth label. Four associated `edge_*_examples.csv` files contain examples and are deliberately not joined into canonical feature tables. The deliberate cases are future leakage, missing-as-negative imputation, outcome/date disagreement, and an unexplained score without human review.

Cardinality is 1:N unless specified; this synthetic baseline has no many-to-many relationship, so no bridge table is needed. Teams and roles on workload records preserve assignment history. Source tables and intervention events are retained as explicit dated records, not overwritten state.
