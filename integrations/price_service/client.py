"""Application client: structured query -> W2 -> quote service -> typed result."""
import argparse
import json
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from saxil_core import Ent, Num, SemanticFrame, decode, encode, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--product-id", type=int, default=1)
    args = parser.parse_args()
    url = urlsplit(args.url)
    if url.scheme != "http" or url.hostname != "127.0.0.1" or url.path != "/quote" or not 1 <= args.product_id <= 255:
        parser.error("Use the loopback /quote URL and a product ID in 1..255")
    query = SemanticFrame(speaker="user", act="ask", intent="query_price", polarity="pos", action="query",
                          object=Ent(eid=args.product_id, typ="product", ref="this"))
    wire = encode(query)
    request = Request(args.url, data=wire, headers={"Content-Type": "application/octet-stream"}, method="POST")
    with urlopen(request, timeout=5) as response:
        if response.headers.get_content_type() != "application/octet-stream":
            raise RuntimeError("Unexpected response media type")
        packet = response.read(4097)
    if len(packet) > 4096 or not validate(packet)["is_canonical_encoding"]:
        raise RuntimeError("Invalid quote response")
    quote = decode(packet)
    if not isinstance(quote, SemanticFrame) or (quote.speaker, quote.act, quote.intent, quote.polarity, quote.action) != ("agent", "assert", "state_price", "pos", "state") or quote.object is None or quote.object.eid != args.product_id or quote.object.typ != "product" or not isinstance(quote.attribute, Num):
        raise RuntimeError("Response does not satisfy the application quote contract")
    print(json.dumps({"product_id": quote.object.eid, "price": quote.attribute.v, "unit": quote.attribute.unit,
                      "request_bytes": len(wire), "response_bytes": len(packet)}, sort_keys=True))


if __name__ == "__main__":
    main()
