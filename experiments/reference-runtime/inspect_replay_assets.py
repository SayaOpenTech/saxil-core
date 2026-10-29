"""Offline read-only identity capture; no model import, GPU or experiment launch.

Run only on the original host through an approved bounded command/launcher.
Current hashes establish current identity, not identity with historical runs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import time
from pathlib import Path

ASSETS = {
    "value_a": "experiments/TML-SV3R2D-R/checkpoints/d1a",
    "value_b": "experiments/TML-SV3R2D-R/checkpoints/d1b",
    "entity_a_frozen_sv3": "models/saxil/qwen3.5-4b-saxil-sv3",
    "entity_b_trained_sv3r": "models/saxil/qwen3.5-4b-saxil-sv3r",
    "entity_b_final_checkpoint_comparison": "experiments/TML-SV3R/checkpoints/final",
}
DATA = {"value_dev": ("experiments/TML-SV3R2D-R/corpus/numeric_dev.jsonl", 450), "entity_test": ("experiments/TML-SV3R/training/test.jsonl", 208)}
SOURCES = (
    "experiments/TML-SV3/sv3/train.py", "experiments/TML-SV3/sv3/model.py", "experiments/TML-SV3/sv3/mapping.py",
    "experiments/TML-SV3R/sv3r/evaluate.py", "experiments/TML-SV3R/sv3r/sidecar.py",
    "experiments/TML-SV3R2D-R/sv3r2d/config.py", "experiments/TML-SV3R2D-R/sv3r2d/evaluate.py",
    "experiments/TML-SV3R2D-R/sv3r2d/value_sidecar.py", "experiments/TML-SV3R2D-R/sv3r2d/mapping.py",
    "experiments/TML-SV3R2D-R/sv3r2d/runtime.py", "experiments/TML-SV3OPT/sv3opt_runtime.py", "harness/paths.py",
)


def contained_file(root: Path, relative: str) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError("non-relative asset path")
    target = (root / raw).resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError("asset outside workspace or not a regular file")
    return target


def inspect(workspace: Path, *, max_seconds: int = 600) -> dict:
    if type(max_seconds) is not int or not 1 <= max_seconds <= 900:
        raise ValueError("inspection budget outside 1..900 seconds")
    root = workspace.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace is not a directory")
    started = time.monotonic()
    files = {}

    def capture(relative):
        if relative in files:
            return files[relative]
        try:
            path = contained_file(root, relative)
            before = path.stat()
            hasher = hashlib.sha256()
            with path.open("rb") as stream:
                while True:
                    if time.monotonic() - started > max_seconds:
                        raise TimeoutError("inspection budget exhausted")
                    block = stream.read(1024 * 1024)
                    if not block:
                        break
                    hasher.update(block)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise RuntimeError("asset changed during inspection")
            result = {"status": "HASHED", "bytes": after.st_size, "sha256": hasher.hexdigest()}
        except FileNotFoundError:
            result = {"status": "MISSING"}
        except TimeoutError:
            result = {"status": "BUDGET_EXHAUSTED"}
        except (OSError, ValueError, RuntimeError) as error:
            result = {"status": "REJECTED", "error_type": type(error).__name__}
        files[relative] = result
        return result

    for directory in ASSETS.values():
        for name in ("adapter/adapter_model.safetensors", "adapter/adapter_config.json", "saxil_extra.pt", "token_mapping.json"):
            capture(directory + "/" + name)
    for relative in SOURCES:
        capture(relative)
    for directory in (ASSETS["entity_a_frozen_sv3"], ASSETS["entity_b_trained_sv3r"]):
        capture(directory + "/tokenizer.json")
    base = "models/saxil/qwen3.5-4b-saxil"
    index_path = base + "/model.safetensors.index.json"
    if capture(index_path)["status"] == "HASHED":
        index = json.loads(contained_file(root, index_path).read_text(encoding="utf-8"))
        shards = sorted(set(index.get("weight_map", {}).values()))
        if not shards or not all(isinstance(name, str) and Path(name).name == name and name.endswith(".safetensors") for name in shards):
            raise ValueError("invalid base-model shard index")
        for name in shards:
            capture(base + "/" + name)
    for name in ("config.json", "tokenizer.json", "tokenizer_config.json"):
        capture(base + "/" + name)
    data = {}
    for tag, (relative, expected) in DATA.items():
        entry = capture(relative)
        if entry["status"] != "HASHED":
            data[tag] = {"status": entry["status"], "expected_rows": expected}
            continue
        rows = [json.loads(line) for line in contained_file(root, relative).read_text(encoding="utf-8").splitlines() if line.strip()]
        ids = [row.get("id") for row in rows]
        valid_ids = all(isinstance(key, str) and key for key in ids)
        passed = len(rows) == expected and valid_ids and len(set(ids)) == expected
        data[tag] = {"status": "COUNTS_AND_IDS_VALID" if passed else "INVALID_COUNTS_OR_IDS", "rows": len(rows), "expected_rows": expected}
    versions = {}
    for name in ("torch", "transformers", "peft", "bitsandbytes", "flash-linear-attention", "causal-conv1d"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {
        "mode": "ASSET_IDENTITY_CAPTURE_ONLY", "python": platform.python_version(),
        "assets": ASSETS, "files": files, "data": data, "installed_versions": versions,
        "all_files_hashed": all(entry["status"] == "HASHED" for entry in files.values()),
        "historical_identity_proved": False, "model_loaded": False,
        "gpu_work_performed": False, "experiment_authorized": False,
        "entity_comparison_caveat": "Frozen SV3 literal versus continued-trained SV3R sidecar; not a same-checkpoint representation ablation",
    }


def write_new_output(workspace: Path, destination: Path, result: dict):
    root = workspace.resolve(strict=True)
    allowed = (root / "artifacts/research/reference_replay_readiness").resolve()
    target = destination.resolve()
    if not allowed.is_relative_to(root) or not target.is_relative_to(allowed) or target == allowed or target.suffix != ".json":
        raise ValueError("output must be a new JSON file under the dedicated artifact root")
    if target.exists():
        raise FileExistsError("refusing to overwrite an inspection result")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-seconds", type=int, default=600)
    args = parser.parse_args()
    result = inspect(args.workspace, max_seconds=args.max_seconds)
    write_new_output(args.workspace, args.output, result)
    print(json.dumps({"all_files_hashed": result["all_files_hashed"], "data": result["data"], "model_loaded": False}))
