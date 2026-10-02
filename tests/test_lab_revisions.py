import unittest

from aquaflow.api import AquaFlowService
from aquaflow.lab.revisions import Result, current


def _payload(results, sample="S1", analyte="chlorine"):
    return {"sample": sample, "analyte": analyte, "results": results}


class RevisionSelectionTest(unittest.TestCase):
    def test_supersession_chain_selects_head(self):
        rows = [
            Result("S1", "chlorine", 0.50, 1),
            Result("S1", "chlorine", 0.85, 2, supersedes=1),
            Result("S1", "chlorine", 0.90, 3, supersedes=2),
        ]
        result = current(rows, "S1", "chlorine")
        self.assertEqual(result.revision, 3)
        self.assertEqual(result.value, 0.90)

    def test_other_samples_do_not_interfere(self):
        rows = [
            Result("S1", "chlorine", 0.50, 1),
            Result("S1", "chlorine", 0.85, 2, supersedes=1),
            # same analyte, different sample: its own chain and values
            Result("S2", "chlorine", 9.99, 1),
            Result("S2", "chlorine", 8.88, 2, supersedes=1),
            # same sample, different analyte
            Result("S1", "fluoride", 7.77, 1),
            # a row in another sample claiming to supersede revision 1
            # must not retire S1's revision 1
            Result("S3", "chlorine", 1.23, 4, supersedes=1),
        ]
        result = current(rows, "S1", "chlorine")
        self.assertEqual(result.revision, 2)
        self.assertEqual(result.value, 0.85)

    def test_competing_active_revisions_rejected(self):
        rows = [
            Result("S1", "chlorine", 0.50, 1),
            Result("S1", "chlorine", 0.85, 2),
        ]
        with self.assertRaises(ValueError):
            current(rows, "S1", "chlorine")

    def test_competing_heads_rejected(self):
        rows = [
            Result("S1", "chlorine", 0.50, 1),
            Result("S1", "chlorine", 0.85, 2, supersedes=1),
            Result("S1", "chlorine", 0.90, 3, supersedes=1),
        ]
        with self.assertRaises(ValueError):
            current(rows, "S1", "chlorine")

    def test_missing_predecessor_rejected(self):
        rows = [Result("S1", "chlorine", 0.85, 2, supersedes=99)]
        with self.assertRaises(ValueError):
            current(rows, "S1", "chlorine")

    def test_predecessor_in_other_sample_is_unresolvable(self):
        rows = [
            Result("S2", "chlorine", 0.50, 1),
            Result("S1", "chlorine", 0.85, 2, supersedes=1),
        ]
        with self.assertRaises(ValueError):
            current(rows, "S1", "chlorine")


class PublishWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.service = AquaFlowService()

    def test_publish_reports_selected_revision_and_value(self):
        response = self.service.run_workflow("lab_revision", _payload([
            {"sample": "S1", "analyte": "chlorine", "value": 0.50, "revision": 1},
            {"sample": "S1", "analyte": "chlorine", "value": 0.85, "revision": 2, "supersedes": 1},
            {"sample": "S2", "analyte": "chlorine", "value": 9.99, "revision": 5},
        ]))
        self.assertEqual(response["decision"], "publish")
        self.assertEqual(response["value"], 2)
        self.assertEqual(response["evidence"]["value"], 0.85)
        self.assertEqual(response["workflow"], "lab_revision")

    def test_publish_rejects_competing_active_revisions(self):
        with self.assertRaises(ValueError):
            self.service.run_workflow("lab_revision", _payload([
                {"sample": "S1", "analyte": "chlorine", "value": 0.50, "revision": 1},
                {"sample": "S1", "analyte": "chlorine", "value": 0.85, "revision": 2},
            ]))

    def test_publish_rejects_missing_predecessor(self):
        with self.assertRaises(ValueError):
            self.service.run_workflow("lab_revision", _payload([
                {"sample": "S1", "analyte": "chlorine", "value": 0.85, "revision": 2, "supersedes": 99},
            ]))


if __name__ == "__main__":
    unittest.main()
