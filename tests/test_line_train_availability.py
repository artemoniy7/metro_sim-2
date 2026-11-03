import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class LineTrainAvailabilityTests(unittest.TestCase):
    def read_json(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_line_train_ids_exist_as_simulator_models(self):
        train_dir = DATA / "trains"
        model_ids = {
            data.get("model_id", data.get("name"))
            for path in train_dir.glob("*.json")
            for data in [self.read_json(path)]
        }
        for line_path in (DATA / "lines").glob("line_*.json"):
            line = self.read_json(line_path)
            for model_id in line.get("available_train_models", []):
                with self.subTest(line=line_path.name, model_id=model_id):
                    self.assertIn(model_id, model_ids)

    def test_known_line_assignments_are_line_specific(self):
        line_1 = self.read_json(DATA / "lines" / "line_1.json")
        line_9 = self.read_json(DATA / "lines" / "line_9.json")
        line_15 = self.read_json(DATA / "lines" / "line_15.json")

        self.assertEqual(set(line_1["available_train_models"]), {"81-717", "81-740"})
        self.assertEqual(line_9["available_train_models"], ["81-760"])
        self.assertEqual(line_15["available_train_models"], [])


if __name__ == "__main__":
    unittest.main()
