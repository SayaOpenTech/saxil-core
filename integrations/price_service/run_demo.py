"""End-to-end released-wheel integration and application-boundary checks."""
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import saxil_core
from saxil_core import Ent, SemanticFrame, encode


def expect_http(url, payload, status, content_type="application/octet-stream"):
    request = Request(url, data=payload, headers={"Content-Type": content_type}, method="POST")
    try:
        with urlopen(request, timeout=5) as response:
            response.read(4097)
    except HTTPError as exc:
        actual = exc.code
        exc.close()
        if actual != status:
            raise RuntimeError(f"Expected HTTP {status}, got {actual}")
    else:
        raise RuntimeError(f"Expected HTTP {status}, got success")
    print(f"boundary check: HTTP {status}")


def main():
    if version("saxil-core") != "0.1.0" or not Path(saxil_core.__file__).resolve().is_relative_to(Path(sysconfig.get_path("purelib")).resolve()):
        raise RuntimeError("Install the released wheel saxil-core==0.1.0")
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as temp:
        ready = Path(temp) / "ready.json"
        process = subprocess.Popen([sys.executable, "-I", str(root / "service.py"), "--requests", "6", "--ready-file", str(ready)])
        try:
            deadline = time.monotonic() + 10
            while not ready.exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Quote service failed to start")
                time.sleep(0.05)
            url = json.loads(ready.read_text(encoding="utf-8"))["url"]
            result = subprocess.run([sys.executable, "-I", str(root / "client.py"), url], capture_output=True, text=True, check=True, timeout=15)
            quote = json.loads(result.stdout)
            if (quote["product_id"], quote["price"], quote["unit"]) != (1, 42000, "toman"):
                raise RuntimeError("Synthetic catalog quote mismatch")
            print(result.stdout.strip())
            query = dict(speaker="user", act="ask", intent="query_price", polarity="pos", action="query", object=Ent(eid=1, typ="product", ref="this"))
            valid = encode(SemanticFrame(**query))
            expect_http(url, b"\x03\x10", 400)
            expect_http(url, encode(SemanticFrame(**{**query, "intent": "greet"})), 422)
            expect_http(url, encode(SemanticFrame(**{**query, "object": Ent(eid=3, typ="product")})), 404)
            expect_http(url, valid, 415, "application/json")
            expect_http(url, b"\x00" * 4097, 413)
            if process.wait(timeout=5) != 0:
                raise RuntimeError("Quote service failed")
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
    print("PASS: published SDK quote integration, separate processes, five boundary checks")


if __name__ == "__main__":
    main()
