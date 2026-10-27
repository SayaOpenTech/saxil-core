"""CPU-only public serialization benchmark; no token or free-text baseline."""
import argparse
from dataclasses import asdict
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sysconfig
import time

import saxil_core
from saxil_core import Ent, SemanticFrame, VerbalUtt, VUnit, decode, encode


def from_data(data):
    values = dict(data)
    kind = values.pop("type")
    if kind == "semantic":
        if "object" in values:
            values["object"] = Ent(**values["object"])
        return SemanticFrame(**values)
    if kind == "verbal":
        values["units"] = tuple(VUnit(**unit) for unit in values["units"])
        return VerbalUtt(**values)
    raise ValueError("Unknown benchmark record type")


def compact(value):
    if isinstance(value, dict):
        return {key: compact(item) for key, item in value.items() if item is not None and item != ()}
    if isinstance(value, (tuple, list)):
        return [compact(item) for item in value]
    return value


def json_encode(frame):
    # Benchmark schema for these fixtures, not a new public SDK API.
    data = compact(asdict(frame))
    data["type"] = "semantic" if isinstance(frame, SemanticFrame) else "verbal"
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def json_decode(packet):
    return from_data(json.loads(packet))


def measure(function, items, iterations, trials):
    for _ in range(3):
        for item in items:
            function(item)
    samples = []
    for _ in range(trials):
        start = time.perf_counter_ns()
        for _ in range(iterations):
            for item in items:
                function(item)
        samples.append(time.perf_counter_ns() - start)
    calls = iterations * len(items)
    return {"calls_per_trial": calls, "trial_duration_ns": samples,
            "median_ns_per_operation": statistics.median(samples) / calls,
            "median_operations_per_second": calls * 1e9 / statistics.median(samples)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 100000 or not 1 <= args.trials <= 20:
        parser.error("Use 1..100000 iterations and 1..20 trials")
    if version("saxil-core") != "0.1.0" or not Path(saxil_core.__file__).resolve().is_relative_to(Path(sysconfig.get_path("purelib")).resolve()):
        raise RuntimeError("Use installed released saxil-core==0.1.0, not the checkout")
    root = Path(__file__).resolve().parent
    corpus = json.loads((root / "corpus.json").read_text(encoding="utf-8"))
    frames = [from_data(record["payload"]) for record in corpus["records"]]
    wires = [encode(frame) for frame in frames]
    documents = [json_encode(frame) for frame in frames]
    rows = []
    for record, frame, wire, document in zip(corpus["records"], frames, wires, documents):
        # Compare all dataclass fields, not just intent or byte roundtrip.
        if asdict(frame) != asdict(decode(wire)) or asdict(frame) != asdict(json_decode(document)):
            raise RuntimeError(f"Semantic-equivalence control failed: {record['id']}")
        if encode(decode(wire)) != wire or json_encode(json_decode(document)) != document:
            raise RuntimeError(f"Canonical representation failed: {record['id']}")
        rows.append({"id": record["id"], "ast_type": type(frame).__name__, "w2_bytes": len(wire), "compact_json_utf8_bytes": len(document)})
    corpus_bytes = json.dumps(corpus, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    result = {
        "schema": "saxil-public-benchmark-v1", "sdk_version": version("saxil-core"),
        "benchmark_source_commit": commit,
        "script_sha256_lf": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        "corpus_sha256_canonical_json": hashlib.sha256(corpus_bytes).hexdigest(),
        "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(), "os": platform.system(), "machine": platform.machine(), "cpu": platform.processor(), "logical_cpu_count": os.cpu_count()},
        "method": {"iterations": args.iterations, "trials": args.trials, "warmup_corpus_passes": 3, "clock": "perf_counter_ns", "semantic_equivalence": "all dataclass fields equal for original, W2-decoded and JSON-decoded AST"},
        "sizes": rows,
        "totals": {"records": len(rows), "w2_bytes": sum(len(p) for p in wires), "compact_json_utf8_bytes": sum(len(p) for p in documents)},
        "timings": {
            "w2_encode": measure(encode, frames, args.iterations, args.trials),
            "w2_decode": measure(decode, wires, args.iterations, args.trials),
            "json_encode_with_ast_projection": measure(json_encode, frames, args.iterations, args.trials),
            "json_decode_with_ast_construction": measure(json_decode, documents, args.iterations, args.trials)},
        "limitations": ["Eight synthetic records are not representative of production workloads.", "Compact JSON includes type/field names; W2 uses a closed schema/vocabulary.", "No arbitrary-text, LLM-token/cost or end-to-end voice performance claim.", "Microbenchmark excludes network, model inference and application processing.", "Validation work differs between codecs; timing is specific to the documented operations.", "CPU load, Python and hardware affect timing; CI has no performance threshold."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"totals": result["totals"], "operations_per_second": {key: round(value["median_operations_per_second"], 1) for key, value in result["timings"].items()}}, indent=2))
    print("PASS: semantic equivalence for every record; raw trials saved")


if __name__ == "__main__":
    main()
