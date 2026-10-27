import csv
import tempfile
import unittest
from pathlib import Path

from workforce_retention.analytics import analyze
from workforce_retention.generator import generate
from workforce_retention.validate import validate


class PipelineTests(unittest.TestCase):
    def test_generation_validity_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / "a", root / "b"
            sa = generate(a, employees_count=25, seed=42)
            sb = generate(b, employees_count=25, seed=42)
            self.assertEqual(sa["files"], sb["files"])
            self.assertEqual(sa["rows"], sb["rows"])
            self.assertEqual(validate(a)["status"], "PASS")
            self.assertGreaterEqual(sa["attrition_rate"], .05)
            self.assertLessEqual(sa["attrition_rate"], .15)

    def test_analysis_produces_explainable_support_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); data = root / "data"
            generate(data, employees_count=20, seed=7)
            metrics = analyze(data, root / "out" / "support.csv")
            with (root / "out" / "support.csv").open(newline="", encoding="utf-8") as f:
                decisions = list(csv.DictReader(f))
            self.assertEqual(len(decisions), 20)
            self.assertIn("human review required", decisions[0]["disclaimer"])
            self.assertTrue(all("reason_codes" in row for row in decisions))
            self.assertEqual(metrics["population"], 20)

    def test_anomaly_truth_is_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); generate(root, employees_count=10, seed=9)
            with (root / "ground_truth.csv").open(newline="", encoding="utf-8") as f:
                cases = list(csv.DictReader(f))
            self.assertEqual(len(cases), 4)
            self.assertEqual({r["issue_type"] for r in cases}, {"future_information_leak", "missing_survey_as_negative", "outcome_date_label_mismatch", "unexplained_individual_score"})


if __name__ == "__main__":
    unittest.main()
