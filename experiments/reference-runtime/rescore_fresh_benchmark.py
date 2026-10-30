"""Independent source-table scoring of hosted model raw outputs."""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "fresh_benchmark_v2"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def no_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate key")
        obj[key] = value
    return obj


def independently_correct(case, arm, raw):
    response = raw.get("response", {})
    if not response.get("choices"):
        return False
    content = response["choices"][0]["message"].get("content") or ""
    try:
        kinds = ("entities", "values")
        if arm == "reference_alias":
            pieces = content.strip().split()
            if len(pieces) != 1 + sum(len(case["request"][kind]) for kind in kinds):
                return False
            parsed = {"action": pieces[0]}
            position = 1
            for kind in kinds:
                parsed[kind] = {}
                for request in case["request"][kind]:
                    parsed[kind][request["role"]] = pieces[position]
                    position += 1
        else:
            parsed = json.loads(content.strip(), object_pairs_hook=no_duplicate_keys)
        if not isinstance(parsed, dict) or set(parsed) != {"action", "entities", "values"} or parsed["action"] != case["request"]["action"]:
            return False
        for kind in kinds:
            result = parsed[kind]
            if not isinstance(result, dict) or set(result) != {r["role"] for r in case["request"][kind]}:
                return False
            for request in case["request"][kind]:
                expected = [record for record in case[kind] if record["role"] == request["role"] and record["label"] == request["label"]]
                assert len(expected) == 1
                if arm == "direct_json":
                    if result[request["role"]] != expected[0]["text"]:
                        return False
                else:
                    # The chosen alias must be the requested source record, not
                    # merely another valid reference with the same type/role.
                    got = [record for record in case[kind] if record["alias"] == result[request["role"]]]
                    if len(got) != 1 or got[0] != expected[0]:
                        return False
        return True
    except (ValueError, TypeError, KeyError, IndexError):
        return False


def main():
    protocol = read(WORK / "protocol.json")
    cases = {case["id"]: case for case in read(WORK / "cases.json")}
    rows = [json.loads(line) for line in (WORK / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == protocol["planned_requests"]
    indexed = {}
    discrepancies = []
    for row in rows:
        key = (row["case_id"], row["arm"], row["seed"])
        assert key not in indexed
        assert row["case_id"] in cases and row["arm"] in protocol["arms"] and row["seed"] in protocol["inference_seeds"]
        actual = independently_correct(cases[row["case_id"]], row["arm"], row)
        if actual != row["exact"]:
            discrepancies.append({"case_id": row["case_id"], "arm": row["arm"], "seed": row["seed"]})
        indexed[key] = int(actual)
    seals_valid = all(hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"] for item in read(WORK / "seal.json")["files"])
    assert seals_valid
    result = {
        "status": "INDEPENDENT_RESCORING_COMPLETE", "distinct_cases": len(cases),
        "responses": len(rows), "score_discrepancies": discrepancies,
        "seal_valid": seals_valid, "historical_checkpoint_replayed": False,
        "providers": dict(Counter(row.get("response", {}).get("provider", "NO_RESPONSE") for row in rows)),
        "models": dict(Counter(row.get("response", {}).get("model", "NO_RESPONSE") for row in rows)),
        "arms": {}, "paired_case_cluster_intervals": [],
    }
    for arm in protocol["arms"]:
        arm_rows = [row for row in rows if row["arm"] == arm]
        failures = [{"case_id": row["case_id"], "seed": row["seed"], "family": row["family"], "content": row.get("response", {}).get("choices", [{}])[0].get("message", {}).get("content", ""), "error": row.get("parse_or_resolve_error") or row.get("http_error") or row.get("transport_error_type")} for row in arm_rows if not indexed[(row["case_id"], arm, row["seed"])]]
        result["arms"][arm] = {"n": len(arm_rows), "correct": sum(indexed[(row["case_id"], arm, row["seed"])] for row in arm_rows), "failures": failures}
    for a, b in (("direct_json", "reference_json"), ("reference_json", "reference_alias")):
        differences = [sum(indexed[(case_id, b, seed)] - indexed[(case_id, a, seed)] for seed in protocol["inference_seeds"]) / len(protocol["inference_seeds"]) for case_id in sorted(cases)]
        rng = random.Random(20261029)
        estimates = sorted(sum(rng.choices(differences, k=len(differences))) / len(differences) for _ in range(10000))
        result["paired_case_cluster_intervals"].append({"a": a, "b": b, "b_minus_a": sum(differences) / len(differences), "bootstrap_95_percent_interval": [estimates[249], estimates[9749]], "clusters": len(cases), "bootstrap_resamples": 10000})
    (WORK / "independent_analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"responses": len(rows), "score_discrepancies": len(discrepancies), "seal_valid": seals_valid, "correct": {arm: result["arms"][arm]["correct"] for arm in protocol["arms"]}, "paired_intervals": result["paired_case_cluster_intervals"]}, indent=2))


if __name__ == "__main__":
    main()
