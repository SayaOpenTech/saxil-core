"""Workflow guard tests; synthetic future-version fixtures, no upload/network/package execution."""

import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import zipfile

import verify_release as v


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.files = self.root / "dist"
        self.files.mkdir()
        metadata = b"Name: saxil-core\nVersion: 9.9.9\n"
        wheel = self.files / "saxil_core-9.9.9-py3-none-any.whl"
        with zipfile.ZipFile(wheel, "w") as z:
            z.writestr("saxil_core-9.9.9.dist-info/METADATA", metadata)
        sdist = self.files / "saxil_core-9.9.9.tar.gz"
        with tarfile.open(sdist, "w:gz") as t:
            member = tarfile.TarInfo("saxil_core-9.9.9/PKG-INFO")
            member.size = len(metadata)
            t.addfile(member, io.BytesIO(metadata))
        self.approval = {"tag": "v9.9.9", "version": "9.9.9", "commit": "a" * 40,
                         "publish_allowed": False, "build": None,
                         "assets": [{"name": p.name, "id": i + 1,
                                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                                    for i, p in enumerate(sorted(self.files.iterdir()))]}

    def test_frozen_baseline_can_be_verified_but_never_published(self):
        self.assertFalse(v.load_approval("v0.1.0", "verify-only")["publish_allowed"])
        with self.assertRaisesRegex(ValueError, "permanently verification-only"):
            v.load_approval("v0.1.0", "publish")

    def test_unsafe_or_noncanonical_tags_rejected(self):
        for tag in ("../v0.1.0", "v00.1.0", "v0.01.0", "v0.1.00", "v0.1.0;echo", "main", "v1.0.0rc1"):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                v.load_approval(tag, "verify-only")

    def test_future_publication_requires_reviewed_build_approval(self):
        (self.root / "v9.9.9.json").write_text(json.dumps(self.approval))
        with patch.object(v, "APPROVALS", self.root), self.assertRaisesRegex(ValueError, "explicit approval"):
            v.load_approval("v9.9.9", "publish")

    def test_valid_hashes_and_both_package_metadata(self):
        v.verify_files(self.files, self.approval)
        v.verify_metadata(self.files, self.approval)

    def test_tampered_file_is_rejected(self):
        (self.files / self.approval["assets"][0]["name"]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "Hash mismatch"):
            v.verify_files(self.files, self.approval)

    def test_unapproved_extra_file_is_rejected(self):
        (self.files / "extra.whl").write_bytes(b"unapproved")
        with self.assertRaisesRegex(ValueError, "Unexpected or missing"):
            v.verify_files(self.files, self.approval)

    def test_wrong_distribution_version_is_rejected(self):
        self.approval["version"] = "9.9.8"
        with self.assertRaisesRegex(ValueError, "metadata"):
            v.verify_metadata(self.files, self.approval)

    def test_existing_pypi_version_cannot_be_published(self):
        with patch.object(v, "pypi_version", return_value={"urls": []}), self.assertRaisesRegex(ValueError, "already exists"):
            v.check_pypi(self.approval, "publish")

    def test_existing_pypi_hashes_must_match(self):
        with patch.object(v, "pypi_version", return_value={"urls": []}), self.assertRaisesRegex(ValueError, "hashes differ"):
            v.check_pypi(self.approval, "verify-only")

    def test_only_http_404_means_unpublished(self):
        with patch.object(v, "urlopen", side_effect=HTTPError("url", 404, "absent", {}, None)):
            self.assertIsNone(v.pypi_version("9.9.9"))
        for error in (HTTPError("url", 500, "error", {}, None), URLError("network down")):
            with patch.object(v, "urlopen", side_effect=error), self.assertRaises(type(error)):
                v.pypi_version("9.9.9")

    def test_publish_authorization_checks_actor_and_rerun_actor(self):
        env = {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
               "GITHUB_REPOSITORY": v.REPO, "RELEASE_AUTHORIZATION": "PUBLISH v9.9.9",
               "GITHUB_ACTOR": "owner", "GITHUB_TRIGGERING_ACTOR": "other"}
        with patch.dict(os.environ, env, clear=True), patch.object(v, "api", return_value={"permission": "admin"}) as api:
            v.authorize("v9.9.9", "publish")
            self.assertEqual(api.call_count, 2)
        # GitHub can report maintain as a role_name over the base write permission.
        with patch.dict(os.environ, env, clear=True), patch.object(v, "api", return_value={"permission": "write", "role_name": "maintain"}):
            v.authorize("v9.9.9", "publish")
        with patch.dict(os.environ, env, clear=True), patch.object(v, "api", return_value={"permission": "write"}):
            with self.assertRaisesRegex(ValueError, "maintainer/admin"):
                v.authorize("v9.9.9", "publish")
        env["GITHUB_REF"] = "refs/tags/v9.9.9"
        with patch.dict(os.environ, env, clear=True), self.assertRaisesRegex(ValueError, "upstream main"):
            v.authorize("v9.9.9", "publish")

    def test_moved_tag_fails_before_artifact_download(self):
        with patch.dict(os.environ, {"RELEASE_TAG": "v0.1.0", "RELEASE_MODE": "verify-only"}), \
                patch.object(v, "api", return_value={"object": {"type": "commit", "sha": "0" * 40}}), \
                self.assertRaisesRegex(ValueError, "Tag moved"):
            v.main()

    def test_future_build_must_match_approved_commit(self):
        self.approval["build"] = {"run_id": 1, "workflow_path": ".github/workflows/build-release.yml", "artifact_name": "dist"}
        run = {"repository": {"full_name": v.REPO}, "head_sha": "b" * 40, "status": "completed",
               "conclusion": "success", "event": "push", "path": ".github/workflows/build-release.yml"}
        with patch.object(v, "api", return_value=run), self.assertRaisesRegex(ValueError, "source build"):
            v.verify_build(self.approval, self.root / "build")

    def test_verifier_rejects_ambient_oidc_credentials(self):
        with patch.dict(os.environ, {"ACTIONS_ID_TOKEN_REQUEST_TOKEN": "synthetic-test-token"}), \
                self.assertRaisesRegex(ValueError, "must not have OIDC"):
            v.main()


if __name__ == "__main__":
    unittest.main()
