"""One-shot loopback receiver. HTTP framing belongs to this example, not W2."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path

from saxil_core import SaxilCoreError, decode, encode


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/w2":
            self.send_error(404)
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
        packet = self.rfile.read(size)
        try:
            response = encode(decode(packet))
        except SaxilCoreError:
            self.send_error(400, "Invalid W2 packet")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--ready-file", type=Path)
    args = parser.parse_args()
    with HTTPServer(("127.0.0.1", args.port), Handler) as server:
        server.timeout = 15
        ready = json.dumps({"url": f"http://127.0.0.1:{server.server_port}/w2"})
        if args.ready_file:
            args.ready_file.write_text(ready, encoding="utf-8")
        print(ready, flush=True)
        server.handle_request()


if __name__ == "__main__":
    main()
