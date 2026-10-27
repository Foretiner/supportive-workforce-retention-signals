# Supportive Workforce Retention Signals

A reproducible, entirely synthetic end-to-end workflow for exploring engagement, tenure, role, and workload signals that may help prioritize supportive retention conversations. It does not make employment decisions, and it uses no sensitive employee attributes or external personal data.

## Requirements

Python 3.10 or newer. The project uses only the Python standard library; no install step is needed.

## Quick start

Run these commands from the project root in PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m workforce_retention.generator --employees 200 --seed 20261022 --out data/generated
python -m workforce_retention.validate --data data/generated
python -m workforce_retention.analytics --data data/generated --out data/analysis/support_recommendations.csv
```

For the requested full baseline volume, use `--employees 10000`. Both modes use the same generator, 24 monthly snapshots (Jan 2024–Dec 2025), and the same 2026 outcome horizon. Default seed: `20261022`.

## Pipeline and rules

1. Master tables (employees, roles, teams) are created before dependent history and event records.
2. Monthly workload and quarterly engagement observations cover 24 months. Missing surveys remain blank with `response_status=Missing`.
3. The 2026 voluntary attrition label is generated from a documented simulated latent risk rule. All model-style features are dated on or before 2025-12-31.
4. Promotion, team, compensation, survey, workload, and intervention history is exported as dated records with deterministic IDs and valid foreign keys.
5. Four deliberate negative scenarios are isolated in `edge_*_examples.csv`; `ground_truth.csv` describes expected treatment. They never enter normal feature inputs.
6. Analysis emits one row per employee with reason codes based on pre-horizon average observed engagement (<=2.8/5) and/or average weekly hours (>50). Missing survey count is shown separately and does not itself raise a negative signal.

The output is a suggestion for an optional supportive check-in, with an explanation and human-review disclaimer. It is not a risk score or an automatic employment action.

## Outputs

Generator CSVs: `employees`, `roles`, `teams`, `tenure_snapshots`, `engagement_surveys`, `workload_snapshots`, `compensation_bands`, `promotion_history`, `attrition_outcomes`, `interventions`, `ground_truth`, and three edge-example tables. JSON outputs include `source_manifest.json` and `validation_summary.json` (row counts and SHA-256 checksums). Analytics creates `support_recommendations.csv` and `evaluation_metrics.json`.

See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for field definitions, key formats, null handling, validation rules, and relationship cardinality.

## Validation and reproducibility

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Generate twice into separate folders using the same employee count and seed. The per-file hashes in each `validation_summary.json` should match. The tests perform this check on a sample, validate key uniqueness, foreign keys, survey missingness, workload arithmetic, and outcome/date consistency. Validation reports errors and exits nonzero when it finds broken constraints.

The evaluation JSON includes population and attrition rate, suggestion volume, and precision/recall against the simulated outcomes. Those are descriptive retrospective metrics, not causal estimates; use a time-based holdout for predictive evaluation.

## Provenance

All rows are generated locally by this project. No public or private datasets are used; `source_manifest.json` records that synthetic-only provenance. The seed controls all random generation.

## Assignment notes

- **Environment:** Python 3.10 or newer; standard library only; tested with the commands above.
- **Verification:** the 10,000-employee dataset contains 240,000 monthly workload rows and 80,000 quarterly survey rows. Validation passed with zero errors. All three unit tests passed. Two full generations with seed `20261022` produced matching per-file SHA-256 checksums. The simulated attrition rate was 9.9%.
- **Assumptions:** the 24-month observation period is Jan 2024–Dec 2025 and the simulated label horizon is calendar year 2026. Role and team catalogs are synthetic. Missing survey scores stay null. Example anomalies are isolated from normal feature inputs.
- **Limitations:** this is a synthetic demonstration, not a production HR system or a validated prediction model. The simulated labels and evaluation metrics do not establish causation or real-world predictive performance. The supportive rules are simple thresholds; a time-based holdout and domain review would be needed before any real use. No real employee data, sensitive attributes, or external datasets are included.
- **AI assistance:** AI coding tools were used as development aids for parts of the generator, validator, analysis workflow, documentation, and verification. The resulting project was checked with the documented tests and data validation. [PROMPT_HISTORY.md](PROMPT_HISTORY.md) contains the additional developer prompt suite supplied for inclusion; those prompts were not run against this implementation.

## Repository layout

The main deliverables are in `src/workforce_retention/`, `tests/`, `data/full/`, and `data/full_analysis/`. `README.md` explains setup and verification; `DATA_DICTIONARY.md` documents entities and fields; `PROMPT_HISTORY.md` contains the supplied developer prompt suite. Local editor settings and Git metadata are excluded from the submission.
