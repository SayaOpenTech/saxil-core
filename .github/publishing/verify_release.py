"""Read-only release verification. Never builds, executes, installs or uploads packages."""

import base64
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import tomllib
from urllib.error import HTTPError
from urllib.request import urlopen
import zipfile

REPO = "SayaOpenTech/saxil-core"
FROZEN = "146ef2bd17474ba405caf2d56f726e38344e14e717b32843e666bdc021e66bad"
APPROVALS = Path(__file__).parent / "approvals"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


def api(path):
    return json.loads(gh("api", f"repos/{REPO}/{path}"))


def source(path, commit):
    return base64.b64decode(api(f"contents/{path}?ref={commit}")["content"])


def load_approval(tag, mode):
    require(mode in ("verify-only", "publish"), "Unknown mode")
    require(re.fullmatch(r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", tag),
            "Expected canonical stable vX.Y.Z tag")
    # Independent of manifest contents: the frozen baseline must NEVER be published here.
    require(not (mode == "publish" and tag == "v0.1.0"), "0.1.0 is permanently verification-only")
    approval = json.loads((APPROVALS / f"{tag}.json").read_text(encoding="utf-8"))
    version = tag[1:]
    require(approval["tag"] == tag and approval["version"] == version, "Version/tag mismatch")
    require(re.fullmatch(r"[0-9a-f]{40}", approval["commit"]), "Expected full commit SHA")
    expected = {f"saxil_core-{version}-py3-none-any.whl", f"saxil_core-{version}.tar.gz"}
    require(len(approval["assets"]) == 2 and {a["name"] for a in approval["assets"]} == expected,
            "Exactly the approved wheel and sdist are required")
    require(all(re.fullmatch(r"[0-9a-f]{64}", a["sha256"]) and isinstance(a["id"], int)
                for a in approval["assets"]), "Invalid asset ID or SHA-256")
    if mode == "publish":
        require(approval["publish_allowed"] is True and approval.get("build"),
                "Future publication needs explicit approval and build evidence")
    return approval


def authorize(tag, mode):
    if mode == "verify-only":
        return
    require(os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
            and os.environ.get("GITHUB_REF") == "refs/heads/main"
            and os.environ.get("GITHUB_REPOSITORY") == REPO,
            "Publication authorization must run manually from upstream main")
    require(os.environ.get("RELEASE_AUTHORIZATION") == f"PUBLISH {tag}", "Missing exact authorization")
    for actor in {os.environ.get("GITHUB_ACTOR"), os.environ.get("GITHUB_TRIGGERING_ACTOR")}:
        require(actor and re.fullmatch(r"[A-Za-z0-9-]+", actor), "Invalid actor")
        permission = api(f"collaborators/{actor}/permission")
        require(permission.get("role_name", permission.get("permission")) in ("admin", "maintain"),
                "Publication requires maintainer/admin authority, including on reruns")


def pypi_version(version):
    try:
        with urlopen(f"https://pypi.org/pypi/saxil-core/{version}/json", timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return None
        raise


def check_pypi(approval, mode):
    existing = pypi_version(approval["version"])
    require(not (mode == "publish" and existing is not None), "Version already exists on PyPI; never retry upload")
    if existing is not None:
        actual = {a["filename"]: a["digests"]["sha256"] for a in existing["urls"]}
        require(actual == {a["name"]: a["sha256"] for a in approval["assets"]}, "Existing PyPI hashes differ")
    return existing


def verify_files(directory, approval):
    expected = {a["name"]: a["sha256"] for a in approval["assets"]}
    require({p.name for p in directory.iterdir()} == set(expected), "Unexpected or missing distribution files")
    for name, digest in expected.items():
        require(hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest, f"Hash mismatch: {name}")


def verify_metadata(directory, approval):
    version = approval["version"]
    for asset in approval["assets"]:
        path = directory / asset["name"]
        if path.suffix == ".whl":
            with zipfile.ZipFile(path) as package:
                names = [n for n in package.namelist() if n.endswith(".dist-info/METADATA")]
                require(len(names) == 1, "Expected one wheel METADATA")
                raw = package.read(names[0])
        else:
            with tarfile.open(path, "r:gz") as package:
                member = package.getmember(f"saxil_core-{version}/PKG-INFO")
                require(member.isfile(), "Expected sdist metadata file")
                raw = package.extractfile(member).read()
        metadata = BytesParser().parsebytes(raw)
        require(metadata["Name"] == "saxil-core" and metadata["Version"] == version,
                "Distribution metadata does not match approved project/version")


def verify_build(approval, directory):
    build = approval.get("build")
    if not build:
        require(approval["tag"] == "v0.1.0" and not approval["publish_allowed"],
                "Only the immutable legacy baseline can omit build-run evidence")
        return None
    require(isinstance(build["run_id"], int), "Expected numeric build run ID")
    run = api(f"actions/runs/{build['run_id']}")
    require(run["repository"]["full_name"] == REPO and run["head_sha"] == approval["commit"]
            and run["status"] == "completed" and run["conclusion"] == "success"
            and run["event"] in ("push", "workflow_dispatch")
            and run["path"] == build["workflow_path"], "Unapproved or unsuccessful source build")
    gh("run", "download", str(build["run_id"]), "--repo", REPO, "--name", build["artifact_name"],
       "--dir", str(directory))
    verify_files(directory, approval)
    return run


def main():
    require(not os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN"), "Verifier must not have OIDC permission")
    tag = os.environ.get("RELEASE_TAG", "v0.1.0")
    mode = os.environ.get("RELEASE_MODE", "verify-only")
    approval = load_approval(tag, mode)
    authorize(tag, mode)
    ref = api(f"git/ref/tags/{tag}")["object"]
    for _ in range(5):
        if ref["type"] != "tag":
            break
        ref = api(f"git/tags/{ref['sha']}")["object"]
    require(ref["type"] == "commit" and ref["sha"] == approval["commit"], "Tag moved or commit mismatch")
    release = api(f"releases/{approval['release_id']}")
    require(release["tag_name"] == tag and not release["draft"] and not release["prerelease"],
            "Release identity/state mismatch")
    names = {a["name"] for a in approval["assets"]}
    require({a["name"] for a in release["assets"]} == names | {"SHA256SUMS"}, "Unexpected release asset set")
    for asset in approval["assets"]:
        live = next(a for a in release["assets"] if a["name"] == asset["name"])
        require(live["id"] == asset["id"] and live["digest"] == f"sha256:{asset['sha256']}",
                "Release asset ID/digest changed")
    project = tomllib.loads(source("pyproject.toml", approval["commit"]).decode())
    require(project["project"]["version"] == approval["version"] and project["project"]["name"] == "saxil-core",
            "Source version/project mismatch")
    spec = source("docs/W2-v1-spec-1.0.md", approval["commit"])
    require(hashlib.sha256(spec.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest() == FROZEN,
            "Frozen specification mismatch (canonical CRLF representation)")
    existing = check_pypi(approval, mode)  # Only HTTP 404 means absent; network errors fail closed.
    directory = Path("dist")
    directory.mkdir(exist_ok=False)
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        for name in sorted(names):
            gh("release", "download", tag, "--repo", REPO, "--pattern", name, "--dir", str(directory))
        gh("release", "download", tag, "--repo", REPO, "--pattern", "SHA256SUMS", "--dir", str(temp))
        lines = (temp / "SHA256SUMS").read_text().splitlines()
        checksums = [line.split() for line in lines if line.strip()]
        require(len(checksums) == 2 and all(len(line) == 2 for line in checksums), "Unexpected SHA256SUMS")
        require({name: digest for digest, name in checksums} == {a["name"]: a["sha256"] for a in approval["assets"]},
                "SHA256SUMS disagrees with reviewed approvals")
        verify_files(directory, approval)
        verify_metadata(directory, approval)
        build = verify_build(approval, temp / "build")
    # Repeat absence check before handing artifacts to the publish job. External races
    # are still rejected by PyPI; the publishing action never skips existing files.
    if mode == "publish":
        check_pypi(approval, mode)
    evidence = {"approval": approval, "approval_sha256": hashlib.sha256((APPROVALS / f"{tag}.json").read_bytes()).hexdigest(),
                "workflow_commit": os.environ.get("GITHUB_SHA"), "mode": mode,
                "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                "release": release, "build": build, "pypi_before": existing}
    Path("publishing-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {tag}: source commit, release identity, frozen spec, package metadata, hashes, PyPI and build evidence")
    print("No package was built, installed, executed or uploaded by this verifier.")


if __name__ == "__main__":
    main()
