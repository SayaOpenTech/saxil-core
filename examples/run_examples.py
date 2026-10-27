"""Run all three examples with the installed released SDK, using no source paths."""
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import time

import saxil_core


def run(path, *args):
    subprocess.run([sys.executable, "-I", str(path), *args], check=True, timeout=20)


def main():
    if version("saxil-core") != "0.1.0":
        raise RuntimeError("Install the released saxil-core==0.1.0 first")
    if not Path(saxil_core.__file__).resolve().is_relative_to(Path(sysconfig.get_path("purelib")).resolve()):
        raise RuntimeError("Examples must use the installed wheel, not a source checkout")
    root = Path(__file__).resolve().parent
    run(root / "roundtrip.py")
    with tempfile.TemporaryDirectory() as temp:
        ready = Path(temp) / "ready.json"
        receiver = subprocess.Popen([sys.executable, "-I", str(root / "service_exchange/receiver.py"), "--ready-file", str(ready)])
        try:
            deadline = time.monotonic() + 10
            while not ready.exists():
                if receiver.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("Receiver failed to become ready")
                time.sleep(0.05)
            url = json.loads(ready.read_text(encoding="utf-8"))["url"]
            run(root / "service_exchange/sender.py", url)
            if receiver.wait(timeout=10) != 0:
                raise RuntimeError("Receiver failed")
        finally:
            if receiver.poll() is None:
                receiver.terminate()
                receiver.wait(timeout=5)
    run(root / "invalid_packets.py")
    print("PASS: all three examples, released saxil-core 0.1.0")


if __name__ == "__main__":
    main()
