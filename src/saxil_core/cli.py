"""Minimal CLI for saxil-core (W2 only). No model inference. Offline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from saxil_core._version import get_version_info
from saxil_core.errors import SaxilCoreError
from saxil_core.w2 import (
    Cmp,
    Date,
    Ent,
    Num,
    SemanticFrame,
    Time,
    VerbalUtt,
    VUnit,
    decode,
    encode,
    validate,
)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_ERROR = 1


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _read_bytes(path: str | None) -> bytes:
    if path is None or path == "-":
        return sys.stdin.buffer.read()
    return Path(path).read_bytes()


def _write_bytes(data: bytes, path: str | None) -> None:
    if path is None or path == "-":
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    else:
        Path(path).write_bytes(data)


def _ast_from_json(obj: dict[str, Any]) -> SemanticFrame | VerbalUtt:
    kind = obj.get("type") or obj.get("kind")
    if kind in ("semantic", "SemanticFrame", "MSG_SEMANTIC"):
        return _semantic_from_dict(obj)
    if kind in ("verbal", "VerbalUtt", "MSG_VERBAL"):
        return _verbal_from_dict(obj)
    raise SaxilCoreError("invalid_input", "JSON must include type=semantic|verbal")


def _ent(d: dict[str, Any] | None) -> Ent | None:
    if not d:
        return None
    return Ent(
        eid=int(d["eid"]),
        typ=str(d["typ"]),
        ref=d.get("ref"),
        name=d.get("name"),
    )


def _num(d: Any) -> Num | None:
    if d is None:
        return None
    if isinstance(d, dict):
        return Num(v=d["v"], unit=d.get("unit"))
    return Num(v=d)


def _time(d: Any) -> Date | Time | None:
    if d is None:
        return None
    if "y" in d:
        return Date(y=int(d["y"]), mo=int(d["mo"]), d=int(d["d"]))
    return Time(
        h=d.get("h"),
        m=d.get("m"),
        rel=d.get("rel"),
        weekday=d.get("weekday"),
        unit=d.get("unit"),
        v=d.get("v"),
    )


def _cmp(d: dict[str, Any] | None) -> Cmp | None:
    if not d:
        return None
    right = d["right"]
    if isinstance(right, dict):
        right = Num(v=right["v"], unit=right.get("unit"))
    return Cmp(op=str(d["op"]), left=str(d["left"]), right=right)


def _semantic_from_dict(obj: dict[str, Any]) -> SemanticFrame:
    known = tuple(_ent(x) for x in obj.get("known") or [] if x)  # type: ignore[misc]
    known = tuple(e for e in known if e is not None)
    return SemanticFrame(
        speaker=str(obj.get("speaker", "user")),
        act=str(obj["act"]),
        intent=str(obj["intent"]),
        polarity=str(obj.get("polarity", "pos")),
        action=obj.get("action"),
        object=_ent(obj.get("object")),
        attribute=obj.get("attribute"),
        time=_time(obj.get("time")),
        affect=obj.get("affect"),
        qtype=obj.get("qtype"),
        request=obj.get("request"),
        cond=_cmp(obj.get("cond")),
        known=known,
        modality=obj.get("modality"),
        uncertainty=obj.get("uncertainty"),
    )


def _verbal_from_dict(obj: dict[str, Any]) -> VerbalUtt:
    units = []
    for u in obj.get("units") or []:
        units.append(
            VUnit(
                op=str(u.get("op") or u.get("kind")),
                w=u.get("w") or u.get("text"),
                v=u.get("v"),
                unit=u.get("unit"),
                spoken=u.get("spoken"),
                mode=u.get("mode"),
                y=u.get("y"),
                mo=u.get("mo"),
                d=u.get("d"),
                h=u.get("h"),
                m=u.get("m"),
                rel=u.get("rel"),
                weekday=u.get("weekday"),
                pause=u.get("pause"),
            )
        )
    return VerbalUtt(utt_type=str(obj.get("utt_type", "statement")), units=tuple(units))


def _ast_to_jsonable(obj: Any) -> dict[str, Any]:
    if isinstance(obj, SemanticFrame):
        return {
            "type": "semantic",
            "speaker": obj.speaker,
            "act": obj.act,
            "intent": obj.intent,
            "polarity": obj.polarity,
            "action": obj.action,
            "object": None
            if obj.object is None
            else {
                "eid": obj.object.eid,
                "typ": obj.object.typ,
                "ref": obj.object.ref,
                "name": obj.object.name,
            },
            "attribute": obj.attribute,
            "time": _time_to_json(obj.time),
            "affect": obj.affect,
            "qtype": obj.qtype,
            "request": obj.request,
            "cond": None
            if obj.cond is None
            else {
                "op": obj.cond.op,
                "left": obj.cond.left,
                "right": obj.cond.right.v
                if isinstance(obj.cond.right, Num)
                else obj.cond.right,
            },
            "known": [
                {"eid": e.eid, "typ": e.typ, "ref": e.ref, "name": e.name} for e in obj.known
            ],
            "modality": obj.modality,
            "uncertainty": obj.uncertainty,
        }
    if isinstance(obj, VerbalUtt):
        units = []
        for u in obj.units:
            units.append(
                {
                    "op": u.op,
                    "w": u.w,
                    "v": u.v,
                    "unit": u.unit,
                    "spoken": u.spoken,
                    "mode": u.mode,
                    "y": u.y,
                    "mo": u.mo,
                    "d": u.d,
                    "h": u.h,
                    "m": u.m,
                    "rel": u.rel,
                    "weekday": u.weekday,
                    "pause": u.pause,
                }
            )
        return {"type": "verbal", "utt_type": obj.utt_type, "units": units}
    return {"type": type(obj).__name__, "repr": repr(obj)}


def _time_to_json(t: Any) -> Any:
    if t is None:
        return None
    if isinstance(t, Date):
        return {"y": t.y, "mo": t.mo, "d": t.d}
    if isinstance(t, Time):
        return {
            "h": t.h,
            "m": t.m,
            "rel": t.rel,
            "weekday": t.weekday,
            "unit": t.unit,
            "v": t.v,
        }
    return repr(t)


def cmd_version(_: argparse.Namespace) -> int:
    info = get_version_info()
    print(json.dumps(info, indent=2, sort_keys=True))
    return EXIT_OK


def cmd_encode(args: argparse.Namespace) -> int:
    raw = sys.stdin.read() if args.input in (None, "-") else Path(args.input).read_text(encoding="utf-8")
    data = json.loads(raw)
    obj = _ast_from_json(data)
    blob = encode(obj, profile=args.profile)
    if args.hex:
        hx = blob.hex()
        if args.output in (None, "-"):
            print(hx)
        else:
            Path(args.output).write_text(hx + "\n", encoding="ascii")
        return EXIT_OK
    _write_bytes(blob, args.output)
    return EXIT_OK


def cmd_decode(args: argparse.Namespace) -> int:
    if args.hex:
        text = sys.stdin.read() if args.input in (None, "-") else Path(args.input).read_text(encoding="ascii")
        blob = bytes.fromhex(text.strip())
    else:
        blob = _read_bytes(args.input)
    obj = decode(blob, profile=args.profile)
    out = _ast_to_jsonable(obj)
    text = json.dumps(out, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output in (None, "-"):
        print(text)
    else:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    return EXIT_OK


def cmd_validate(args: argparse.Namespace) -> int:
    if args.hex:
        text = sys.stdin.read() if args.input in (None, "-") else Path(args.input).read_text(encoding="ascii")
        blob = bytes.fromhex(text.strip())
    else:
        blob = _read_bytes(args.input)
    report = validate(blob, profile=args.profile)
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="saxil",
        description="saxil-core CLI - W2 encode/decode/validate (PUBLIC)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("version", help="Show software/protocol/profile versions (JSON)")
    sp.set_defaults(func=cmd_version)

    pe = sub.add_parser("encode", help="Encode JSON AST to W2 bytes")
    pe.add_argument("-i", "--input", default="-", help="JSON AST path or - for stdin")
    pe.add_argument("-o", "--output", default="-", help="Output path or - for stdout")
    pe.add_argument("--hex", action="store_true", help="Write hex text instead of raw bytes")
    pe.add_argument("--profile", default="W2-v1")
    pe.set_defaults(func=cmd_encode)

    pd = sub.add_parser("decode", help="Decode W2 bytes to JSON AST")
    pd.add_argument("-i", "--input", default="-", help="Binary path or - for stdin")
    pd.add_argument("-o", "--output", default="-", help="JSON output path or -")
    pd.add_argument("--hex", action="store_true", help="Input is hex text")
    pd.add_argument("--pretty", action="store_true")
    pd.add_argument("--profile", default="W2-v1")
    pd.set_defaults(func=cmd_decode)

    pv = sub.add_parser("validate", help="Validate W2 payload (JSON report)")
    pv.add_argument("-i", "--input", default="-")
    pv.add_argument("--hex", action="store_true")
    pv.add_argument("--profile", default="W2-v1")
    pv.set_defaults(func=cmd_validate)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SaxilCoreError as exc:
        _err(f"error: {exc}")
        return EXIT_ERROR
    except json.JSONDecodeError as exc:
        _err(f"error: invalid_json: {exc}")
        return EXIT_ERROR
    except BrokenPipeError:
        return EXIT_OK
    except Exception as exc:  # noqa: BLE001
        _err(f"error: {type(exc).__name__}: {exc}")
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
