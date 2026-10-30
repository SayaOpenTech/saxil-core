"""Validate every frozen packet/AST and byte claim offline on the public matrix."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "experiments/w2-comparison"
pytestmark = pytest.mark.skipif(
    not STUDY.is_dir(),
    reason="Optional comparative-study fixtures are excluded from SDK distributions",
)


def test_frozen_w2_json_semantics_and_byte_counts(tmp_path):
    archive = STUDY / "study-artifacts.tar.gz"
    expected = (STUDY / "study-artifacts.sha256").read_text().split()[0]
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected
    with tarfile.open(archive) as handle:
        members = handle.getmembers()
        assert sum(item.size for item in members) <= 50_000_000
        for member in members:
            assert member.isfile() and member.size <= 20_000_000
            target = (tmp_path / member.name).resolve()
            assert target.is_relative_to(tmp_path.resolve())
            reader = handle.extractfile(member)
            assert reader is not None
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(reader.read())
    for name in (
        "audit_results.py", "json_controls.py", "build_corpus.py", "run_study.py",
        "PRE_REGISTERED_PROTOCOL.json",
    ):
        shutil.copyfile(STUDY / name, tmp_path / name)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-B", "audit_results.py", "--verify-frozen"],
        cwd=tmp_path, env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PORTABLE_FROZEN_PACKET_AUDIT_PASSED" in result.stdout
