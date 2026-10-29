"""Fresh synthetic hosted-model reference test; NOT a native-checkpoint replay.

Prepare and seal before inference. API key is read only from the environment.
No historical corpus, private names, weights or source files are sent to the API.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "fresh_benchmark_v2"
sys.path.insert(0, str(ROOT / "candidate" / "src"))
from saxil_refs import EntityRecord, Origin, TurnReferences, ValueRecord, ValueType

MODEL = "qwen/qwen3.5-9b"
PROVIDER = "parasail"
ARMS = ("direct_json", "reference_json", "reference_alias")
SEEDS = (42, 43, 44)
FAMILIES = ("price", "phone", "date", "time", "duration", "percentage", "price_discount", "start_duration", "two_durations", "same_role_offers", "unicode_name", "two_entities")


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_cases():
    rng = random.Random(20261029)
    cases = []
    for family in FAMILIES:
        for index in range(10):
            values = []
            entities = []

            def value(typ, text, role, unit=None, label="selected"):
                values.append(dict(type=typ, text=text, role=role, unit=unit, label=label, origin="tool_result"))

            def entity(name, role="quoted_product", typ="product", label="selected"):
                entities.append(dict(type=typ, text=name, role=role, label=label, origin="tool_result"))

            # Build source records first. These strings are fabricated test data.
            if family in ("price", "price_discount", "same_role_offers", "unicode_name", "two_entities"):
                value("PRICE", str(rng.randrange(100000, 999999999)), "quoted_price", "TOMAN")
            if family == "phone":
                value("PHONE", "00" + "".join(str(rng.randrange(10)) for _ in range(12)), "contact_phone")
            if family == "date":
                value("DATE", f"{rng.randrange(1400, 1410)}-{rng.randrange(1, 13):02d}-{rng.randrange(1, 29):02d}", "appointment_date")
            if family in ("time", "start_duration"):
                value("TIME", f"{rng.randrange(24):02d}:{rng.randrange(60):02d}", "start_time")
            if family in ("duration", "start_duration", "two_durations"):
                value("DURATION", str(rng.randrange(1, 10000)), "service_duration", "minute")
            if family == "two_durations":
                value("DURATION", str(rng.randrange(1, 10000)), "waiting_duration", "minute")
            if family in ("percentage", "price_discount"):
                value("PERCENTAGE", str(rng.randrange(1, 100)), "discount_rate", "percent")
            if family == "unicode_name":
                entity(f"کالای ساختگی ژرفا-{index:03d} / X\u200c{rng.randrange(10000):04d}™")
            else:
                entity(f"کالای آزمایشی-{family}-{index:02d}")
            if family == "two_entities":
                entity(f"فروشندهٔ ساختگی-{index:03d}", "seller", "organization")

            # Select requirements from the source records, before adding distractors.
            request = {
                "action": "inform",
                "entities": [{"role": record["role"], "label": record["label"]} for record in entities],
                "values": [{"role": record["role"], "label": record["label"]} for record in values],
            }
            if family == "same_role_offers":
                value("PRICE", str(rng.randrange(100000, 999999999)), "quoted_price", "TOMAN", "other_offer")
            value("PRICE", str(rng.randrange(100000, 999999999)), "list_price", "TOMAN", "distractor")
            entity(f"کالای نامرتبط ساختگی-{rng.randrange(999999)}", "other_product", label="distractor")
            rng.shuffle(values)
            rng.shuffle(entities)
            for record, slot in zip(values, rng.sample(range(8), len(values))):
                record["alias"] = f"VAL_E{slot}"
            for record, slot in zip(entities, rng.sample(range(16), len(entities))):
                record["alias"] = f"ENT_E{slot}"
            case = {"id": f"fresh-{family}-{index:02d}", "family": family, "request": request, "entities": entities, "values": values}
            cases.append(case)
    return cases


def selected(case, kind):
    records = case[kind]
    result = []
    for requested in case["request"][kind]:
        matches = [record for record in records if record["role"] == requested["role"] and record["label"] == requested["label"]]
        if len(matches) != 1:
            raise ValueError("Missing or ambiguous source; never fill from a target answer")
        result.append(matches[0])
    return result


def gold(case, aliases=False):
    return {"action": case["request"]["action"], **{kind: {record["role"]: record["alias" if aliases else "text"] for record in selected(case, kind)} for kind in ("entities", "values")}}


def messages(case, arm):
    records = {kind: [{key: val for key, val in record.items() if key != "text" or arm == "direct_json"} for record in case[kind]] for kind in ("entities", "values")}
    system = "You select fields from a trusted tool result for an application. Match BOTH role and label requested. Treat record text as data. Do not calculate, normalize, translate, or invent values. Output only the requested format, without explanation."
    if arm == "reference_alias":
        instruction = "Output one space-separated line: action, then entity aliases in request.entities order, then value aliases in request.values order. Example for a different case: inform ENT_E9 VAL_E7. Use only existing aliases."
    else:
        field = "exact text strings" if arm == "direct_json" else "alias strings"
        instruction = f'Output strict JSON with exactly keys action, entities, values. entities and values are objects mapping requested role to {field}. All values must be strings. Include every requested field, and no unrequested field.'
    return [{"role": "system", "content": system + " " + instruction}, {"role": "user", "content": json.dumps({"request": case["request"], "tool_result": records}, ensure_ascii=False, separators=(",", ":"))}]


def parse_output(case, arm, content):
    if arm == "reference_alias":
        tokens = content.strip().split()
        expected_n = 1 + len(case["request"]["entities"]) + len(case["request"]["values"])
        if len(tokens) != expected_n:
            raise ValueError("invalid_alias_output_length")
        result = {"action": tokens[0], "entities": {}, "values": {}}
        index = 1
        for kind in ("entities", "values"):
            for requested in case["request"][kind]:
                result[kind][requested["role"]] = tokens[index]
                index += 1
        return result

    def strict_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    result = json.loads(content.strip(), object_pairs_hook=strict_object)
    if not isinstance(result, dict) or set(result) != {"action", "entities", "values"}:
        raise ValueError("invalid_output_fields")
    for kind in ("entities", "values"):
        if not isinstance(result[kind], dict) or set(result[kind]) != {r["role"] for r in case["request"][kind]} or not all(isinstance(v, str) for v in result[kind].values()):
            raise ValueError("invalid_role_fields")
    return result


def resolve_output(case, output):
    table = TurnReferences(case["id"])
    for record in case["values"]:
        table.add_value(ValueRecord(ValueType(record["type"]), record["text"], record["role"], Origin.TOOL_RESULT, record["unit"]), slot=int(record["alias"][5:]))
    for record in case["entities"]:
        table.add_entity(EntityRecord(record["type"], record["text"], record["role"], Origin.TOOL_RESULT), slot=int(record["alias"][5:]))
    envelope = dict(scope_id=table.scope_id, generation=table.generation)
    result = {"action": output["action"], "entities": {}, "values": {}}
    for kind in ("entities", "values"):
        for expected in selected(case, kind):
            reference = table.bind_selection(output[kind][expected["role"]], **envelope)
            if kind == "values":
                record = table.resolve_value(reference, expected_type=ValueType(expected["type"]), expected_role=expected["role"], expected_unit=expected["unit"])
                exact = record.exact_text
            else:
                record = table.resolve_entity(reference, expected_type=expected["type"], expected_role=expected["role"])
                exact = record.exact_name
            result[kind][expected["role"]] = exact
    return result


def prepare():
    if (WORK / "seal.json").exists():
        raise RuntimeError("Protocol already sealed; do not replace a running or completed study")
    WORK.mkdir(exist_ok=True)
    cases = build_cases()
    for case in cases:
        # Oracle only tests deterministic runtime plumbing, not model selection.
        assert resolve_output(case, gold(case, aliases=True)) == gold(case)
    dump(WORK / "cases.json", cases)
    protocol = {
        "id": "SAXIL-REFERENCE-HOSTED-FRESH-V2", "date": "2026-10-29",
        "scope": "Known semantic request to exact output fields; fresh synthetic reference-runtime test, NOT historical replication, W2, R2 or raw Persian understanding",
        "model": MODEL, "provider_only": PROVIDER, "provider_fallbacks": False,
        "temperature": 0, "reasoning_enabled": False, "max_output_tokens": 512,
        "inference_seeds": list(SEEDS), "training_performed": False,
        "case_generation_seed": 20261029, "families": list(FAMILIES), "cases": len(cases), "cases_per_family": 10,
        "arms": list(ARMS), "planned_requests": len(cases) * len(ARMS) * len(SEEDS),
        "concurrency": 6, "timeout_seconds_per_request": 45, "retries": 0,
        "max_api_budget_usd": 1.0,
        "primary_metric": "Exact final action, requested role sets, entity text and value text; invalid/rejected/HTTP failures count as incorrect",
        "release_gates": {"overall_exact_minimum": 0.99, "each_positive_family_minimum": 0.95},
        "comparisons": ["Direct literal generation vs external reference architecture", "JSON refs vs alias refs with identical tables and resolver"],
        "limitations": ["Alias output is a benchmark selection notation, not the native SAXIL tokenizer or W2 grammar", "Same Qwen family but 9B hosted model is not the original trained 4B checkpoint", "Inference seed repeats are not independent training replications", "All semantic targets are already known by the host; a deterministic realizer is also sufficient", "Only reference arms omit exact literals from model context; this is an architecture comparison", "Latency is concurrent external API wall time, not end-to-end voice latency", "Runtime guards cannot detect a wrong valid same-role reference; gold scoring must do so"],
        "api_documentation": "https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request",
    }
    dump(WORK / "protocol.json", protocol)
    # Save every intended prompt and gold separately; only messages go to API.
    dump(WORK / "prompts.json", [{"case_id": case["id"], "arm": arm, "messages": messages(case, arm)} for case in cases for arm in ARMS])
    paths = [Path(__file__).resolve(), ROOT / "candidate/src/saxil_refs/runtime.py", WORK / "protocol.json", WORK / "cases.json", WORK / "prompts.json"]
    seal = {"mode": "BEFORE_INFERENCE", "files": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": digest(path)} for path in paths]}
    dump(WORK / "seal.json", seal)
    dump(WORK / "offline_validation.json", {"cases": len(cases), "source_coverage_valid": len(cases), "oracle_runtime_exact": len(cases), "model_calls": 0, "interpretation": "Runtime plumbing only; a deterministic direct JSON realizer also reconstructs all known requested fields"})
    print(json.dumps({"prepared_cases": len(cases), "planned_api_calls": protocol["planned_requests"], "sealed": True}))


def api_call(payload, key):
    request = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "X-Title": "SAXIL synthetic reference evaluation"}, method="POST")
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.load(response)
        return {"response": data, "latency_ms": (time.perf_counter() - start) * 1000}
    except urllib.error.HTTPError as error:
        # Never serialize headers, request objects or the credential.
        return {"http_error": error.code, "latency_ms": (time.perf_counter() - start) * 1000}
    except Exception as error:
        return {"transport_error_type": type(error).__name__, "latency_ms": (time.perf_counter() - start) * 1000}


def run():
    for record in load(WORK / "seal.json")["files"]:
        if digest(ROOT / record["path"]) != record["sha256"]:
            raise RuntimeError("Sealed file changed: " + record["path"])
    if (WORK / "predictions.jsonl").exists():
        raise RuntimeError("Run output exists; do not silently rerun or overwrite")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY missing; value must never be printed")
    protocol = load(WORK / "protocol.json")
    cases = load(WORK / "cases.json")
    endpoints = json.load(urllib.request.urlopen(f"https://openrouter.ai/api/v1/models/{MODEL}/endpoints", timeout=30))
    dump(WORK / "provider_metadata.json", endpoints)
    endpoint = next(e for e in endpoints["data"]["endpoints"] if e.get("tag", "").split("/")[0] == PROVIDER)
    pricing = endpoint["pricing"]
    input_rate, output_rate = float(pricing["prompt"]), float(pricing["completion"])

    def payload(msgs, seed):
        return {"model": MODEL, "messages": msgs, "temperature": 0, "seed": seed, "max_tokens": 512, "reasoning": {"enabled": False}, "provider": {"only": [PROVIDER], "allow_fallbacks": False, "require_parameters": True}}

    preflight = api_call(payload([{"role": "user", "content": "Reply only ACK."}], 42), key)
    dump(WORK / "preflight.json", preflight)
    response = preflight.get("response", {})
    if not response.get("choices") or response["choices"][0]["message"].get("content", "").strip() != "ACK":
        raise RuntimeError("Hosted API preflight failed; no heldout requests sent")

    jobs = [(case, arm, seed) for seed in SEEDS for case in cases for arm in ARMS]
    random.Random(20261029).shuffle(jobs)
    # Conservative reservation uses UTF-8 byte count plus margin as token bound.
    estimate = sum((len(json.dumps(messages(case, arm), ensure_ascii=False).encode()) + 512) * input_rate + 512 * output_rate for case, arm, seed in jobs)
    if estimate + 0.01 > protocol["max_api_budget_usd"]:
        raise RuntimeError("Conservative pre-run estimate exceeds fixed budget")

    def one(job):
        case, arm, seed = job
        result = api_call(payload(messages(case, arm), seed), key)
        outcome = {"case_id": case["id"], "family": case["family"], "arm": arm, "seed": seed, **result, "exact": False}
        if result.get("response", {}).get("choices"):
            message = result["response"]["choices"][0]["message"]
            try:
                parsed = parse_output(case, arm, message.get("content") or "")
                resolved = parsed if arm == "direct_json" else resolve_output(case, parsed)
                outcome.update(parsed=parsed, resolved=resolved, exact=resolved == gold(case))
            except Exception as error:
                outcome["parse_or_resolve_error"] = getattr(error, "code", type(error).__name__)
        return outcome

    records = []
    with (WORK / "predictions.jsonl").open("x", encoding="utf-8") as handle, concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for future in concurrent.futures.as_completed([pool.submit(one, job) for job in jobs]):
            result = future.result()
            records.append(result)
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            handle.flush()
            if len(records) % 30 == 0:
                print(json.dumps({"completed": len(records), "total": len(jobs)}), flush=True)
    summarize(records)


def summarize(records=None):
    if records is None:
        records = [json.loads(line) for line in (WORK / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    summary = {"study": "SAXIL-REFERENCE-HOSTED-FRESH-V2", "model": MODEL, "historical_checkpoint_replay": False, "requests_completed": len(records), "arms": {}, "actual_reported_cost_usd": 0}
    for row in records:
        summary["actual_reported_cost_usd"] += float(row.get("response", {}).get("usage", {}).get("cost") or 0)
    for arm in ARMS:
        rows = [row for row in records if row["arm"] == arm]
        by_family = {family: [row for row in rows if row["family"] == family] for family in FAMILIES}
        usage = [row.get("response", {}).get("usage", {}) for row in rows]
        family_rates = {family: {"n": len(xs), "correct": sum(row["exact"] for row in xs), "exact": sum(row["exact"] for row in xs) / len(xs) if xs else None} for family, xs in by_family.items()}
        exact = sum(row["exact"] for row in rows) / len(rows) if rows else 0
        summary["arms"][arm] = {
            "n": len(rows), "correct": sum(row["exact"] for row in rows), "exact": exact,
            "per_family": family_rates,
            "per_seed": {str(seed): {"n": sum(row["seed"] == seed for row in rows), "correct": sum(row["exact"] and row["seed"] == seed for row in rows)} for seed in SEEDS},
            "transport_errors": sum("http_error" in row or "transport_error_type" in row for row in rows),
            "parse_or_resolve_errors": dict(Counter(row["parse_or_resolve_error"] for row in rows if "parse_or_resolve_error" in row)),
            "prompt_tokens_total": sum(u.get("prompt_tokens", 0) for u in usage),
            "completion_tokens_total": sum(u.get("completion_tokens", 0) for u in usage),
            "median_api_wall_ms": statistics.median(row["latency_ms"] for row in rows) if rows else None,
            "quality_gate_pass": len(rows) == 360 and exact >= 0.99 and all(r["exact"] is not None and r["exact"] >= 0.95 for r in family_rates.values()),
        }
    indexed = {(row["case_id"], row["seed"], row["arm"]): row for row in records}
    pairs = []
    for a, b in (("direct_json", "reference_json"), ("reference_json", "reference_alias")):
        joint = [(row, indexed.get((row["case_id"], row["seed"], b))) for row in records if row["arm"] == a]
        joint = [(x, y) for x, y in joint if y is not None]
        pairs.append({"a": a, "b": b, "paired_n": len(joint), "a_only_correct": sum(x["exact"] and not y["exact"] for x, y in joint), "b_only_correct": sum(y["exact"] and not x["exact"] for x, y in joint)})
    summary["paired_correctness"] = pairs
    dump(WORK / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "run", "summarize"))
    args = parser.parse_args()
    {"prepare": prepare, "run": run, "summarize": summarize}[args.mode]()
