"""Send structured W2 bytes to the local receiver and validate its response."""
import argparse
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from saxil_core import SemanticFrame, decode, encode, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Loopback URL printed by receiver.py")
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.path != "/w2":
        parser.error("Use the http://127.0.0.1:PORT/w2 receiver URL")
    frame = SemanticFrame(speaker="user", act="ask", intent="query_price", polarity="pos", action="query")
    wire = encode(frame)
    request = Request(args.url, data=wire, headers={"Content-Type": "application/octet-stream"}, method="POST")
    with urlopen(request, timeout=5) as response:
        packet = response.read(4097)
    if len(packet) > 4096 or packet != wire or not validate(packet)["is_canonical_encoding"]:
        raise RuntimeError("Receiver response did not preserve the canonical packet")
    print(f"two-service exchange: {len(packet)} bytes, intent={decode(packet).intent}")


if __name__ == "__main__":
    main()
