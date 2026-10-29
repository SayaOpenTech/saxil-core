"""Run isolated experimental checks through the existing public CI matrix."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import pytest


EXPERIMENT = Path(__file__).resolve().parents[1] / "experiments/reference-runtime"
pytestmark = pytest.mark.skipif(
    not EXPERIMENT.is_dir(),
    reason="Optional research fixtures are excluded from public SDK distributions",
)


def _run(arguments, cwd, *, source=None):
    environment = dict(os.environ)
    if source is not None:
        environment["PYTHONPATH"] = str(source)
    result = subprocess.run(
        [sys.executable, "-B", *arguments], cwd=cwd, env=environment,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_reference_runtime_behavior():
    _run(["-m", "unittest", "discover", "-s", "candidate/tests", "-v"], EXPERIMENT, source=EXPERIMENT / "candidate/src")


def test_read_only_replay_inspection():
    _run(["-m", "unittest", "test_inspect_replay_assets", "-v"], EXPERIMENT)


def test_frozen_hosted_evidence_rescores_offline(tmp_path):
    archive = EXPERIMENT / "study-artifacts.tar.gz"
    expected = (EXPERIMENT / "study-artifacts.sha256").read_text().split()[0]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected
    with tarfile.open(archive) as handle:
        for member in handle:
            assert member.isfile()
            target = (tmp_path / member.name).resolve()
            assert target.is_relative_to(tmp_path.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            reader = handle.extractfile(member)
            assert reader is not None
            target.write_bytes(reader.read())
    for name in (
        "fresh_reference_benchmark.py", "fresh_reference_benchmark_v2.py",
        "candidate/src/saxil_refs/runtime.py", "rescore_fresh_benchmark.py",
    ):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(EXPERIMENT / name, target)
    _run(["rescore_fresh_benchmark.py"], tmp_path)
