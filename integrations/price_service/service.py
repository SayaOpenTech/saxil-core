"""Synthetic loopback quote service consuming and producing public W2 frames."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import socket

from saxil_core import Ent, Num, SemanticFrame, SaxilCoreError, decode, encode


class QuoteHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/quote":
            self.send_error(404)
            return
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/octet-stream":
            self.send_error(415, "Expected application/octet-stream")
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if not 0 < size <= 4096:
            self.send_error(413)
            return
        self.connection.settimeout(5)
        try:
            body = self.rfile.read(size)
            request = decode(body)
        except (SaxilCoreError, socket.timeout):
            self.send_error(400, "Invalid or incomplete W2 request")
            return
        if not isinstance(request, SemanticFrame) or (request.speaker, request.act, request.intent, request.polarity, request.action) != ("user", "ask", "query_price", "pos", "query") or request.object is None or request.object.typ != "product":
            self.send_error(422, "Unsupported quote request")
            return
        quote = self.server.catalog.get(str(request.object.eid))
        if quote is None:
            self.send_error(404, "Unknown synthetic product")
            return
        response = SemanticFrame(speaker="agent", act="assert", intent="state_price", polarity="pos", action="state",
                                 object=Ent(eid=request.object.eid, typ="product"),
                                 attribute=Num(v=quote["price"], unit=quote["unit"]))
        wire = encode(response)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(wire)))
        self.end_headers()
        self.wfile.write(wire)

    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--requests", type=int, default=1)
    parser.add_argument("--ready-file", type=Path)
    args = parser.parse_args()
    if not 1 <= args.requests <= 20:
        parser.error("Use 1..20 requests for this finite demo")
    catalog = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))
    with HTTPServer(("127.0.0.1", args.port), QuoteHandler) as server:
        server.catalog = catalog["items"]
        server.timeout = 15
        ready = json.dumps({"url": f"http://127.0.0.1:{server.server_port}/quote"})
        if args.ready_file:
            args.ready_file.write_text(ready, encoding="utf-8")
        print(ready, flush=True)
        for _ in range(args.requests):
            server.handle_request()


if __name__ == "__main__":
    main()
