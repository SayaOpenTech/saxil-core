"""Example 1: a structured frame and its canonical W2 bytes."""
from saxil_core import SemanticFrame, decode, encode, validate


def main():
    frame = SemanticFrame(speaker="user", act="ask", intent="query_price", polarity="pos", action="query")
    wire = encode(frame)
    restored = decode(wire)
    if encode(restored) != wire or not validate(wire)["is_canonical_encoding"]:
        raise RuntimeError("Canonical roundtrip failed")
    print(f"roundtrip: {len(wire)} bytes, intent={restored.intent}, hex={wire.hex()}")


if __name__ == "__main__":
    main()
