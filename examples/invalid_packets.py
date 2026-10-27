"""Example 3: reject malformed/unsupported packets through public SDK errors."""
from saxil_core import SemanticFrame, SaxilCoreError, decode, encode


def main():
    valid = encode(SemanticFrame(speaker="user", act="ask", intent="query_price", polarity="pos"))
    cases = {
        "empty": b"",
        "truncated": valid[:-1],
        "unsupported version": b"\x03" + valid[1:],
        "unknown message type": valid[:1] + b"\xff" + valid[2:],
    }
    for name, packet in cases.items():
        try:
            decode(packet)
        except SaxilCoreError as exc:
            # Catch the public base error; do not silently replace the packet.
            print(f"{name}: rejected ({type(exc).__name__}, code={exc.code})")
        else:
            raise RuntimeError(f"Unexpected acceptance: {name}")


if __name__ == "__main__":
    main()
