import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from inspect_replay_assets import contained_file, inspect, write_new_output


class InspectionTests(unittest.TestCase):
    def test_captures_bytes_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p = root / "models/saxil/qwen3.5-4b-saxil/config.json"
            p.parent.mkdir(parents=True)
            p.write_bytes(b'{"fixture":true}')
            before = p.stat().st_mtime_ns
            result = inspect(root)
            self.assertEqual(result["files"][str(p.relative_to(root)).replace("\\", "/")]["sha256"], hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertEqual(p.stat().st_mtime_ns, before)
            self.assertFalse(result["all_files_hashed"])
            self.assertFalse(result["model_loaded"])

    def test_missing_weights_are_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            result = inspect(Path(directory))
            self.assertTrue(all(record["status"] == "MISSING" for record in result["files"].values()))
            self.assertFalse(result["historical_identity_proved"])

    def test_parent_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                contained_file(Path(directory), "../other")

    def test_shard_index_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = root / "models/saxil/qwen3.5-4b-saxil/model.safetensors.index.json"
            index.parent.mkdir(parents=True)
            index.write_text(json.dumps({"weight_map": {"x": "../../outside.safetensors"}}))
            with self.assertRaises(ValueError):
                inspect(root)

    def test_duplicate_case_ids_reject_data_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "experiments/TML-SV3R2D-R/corpus/numeric_dev.jsonl"
            data.parent.mkdir(parents=True)
            data.write_text('\n'.join(json.dumps({"id": "duplicate"}) for _ in range(450)))
            result = inspect(root)
            self.assertEqual(result["data"]["value_dev"]["status"], "INVALID_COUNTS_OR_IDS")

    def test_output_scope_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                write_new_output(root, root / "models/manifest.json", {})
            destination = root / "artifacts/research/reference_replay_readiness/fixture/result.json"
            write_new_output(root, destination, {"inspection": True})
            with self.assertRaises(FileExistsError):
                write_new_output(root, destination, {})
            self.assertEqual(json.loads(destination.read_text()), {"inspection": True})


if __name__ == "__main__":
    unittest.main()
