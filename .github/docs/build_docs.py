"""Build public docs from a temporary allowlist, preserving frozen source bytes."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs/W2-v1-spec-1.0.md"
EXPECTED = "146ef2bd17474ba405caf2d56f726e38344e14e717b32843e666bdc021e66bad"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.targets.append(value)


def verify_site(site):
    checked = 0
    for page in site.rglob("*.html"):
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        for target in parser.targets:
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            path = unquote(url.path)
            if path.startswith("/saxil-core/"):
                local = site / path[len("/saxil-core/"):]
            elif path.startswith("/"):
                local = site / path.lstrip("/")
            else:
                local = page.parent / path
            if local.is_dir():
                local /= "index.html"
            if not local.is_file():
                raise RuntimeError(f"Broken built link: {page.relative_to(site)} -> {target}")
            checked += 1
    print(f"Verified {checked} local built HTML/asset links")


def main():
    original_spec = SPEC.read_bytes()
    # The frozen manifest uses canonical CRLF, as does the release verifier.
    canonical_spec = original_spec.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    if hashlib.sha256(canonical_spec).hexdigest() != EXPECTED:
        raise RuntimeError("Frozen specification hash mismatch")
    site = ROOT / "site"
    with tempfile.TemporaryDirectory(prefix="saxil-public-docs-") as temp:
        stage = Path(temp) / "docs"
        stage.mkdir()
        for name in ["README.md", "SECURITY.md", "CONTRIBUTING.md", "CHANGELOG.md", "LICENSE", "NOTICE", "DCO.txt"]:
            shutil.copyfile(ROOT / name, stage / name)
        shutil.copyfile(ROOT / "README.md", stage / "index.md")
        for folder in ["docs", "examples", "benchmarks", "integrations"]:
            source = ROOT / folder
            if not source.exists():
                continue
            for path in source.rglob("*"):
                if path.is_file() and path.suffix in {".md", ".json", ".py", ".csv"} and "__pycache__" not in path.parts:
                    if path.is_symlink():
                        raise RuntimeError("Symlinks are not documentation sources")
                    target = stage / path.relative_to(ROOT)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
        if (stage / "docs/W2-v1-spec-1.0.md").read_bytes() != SPEC.read_bytes():
            raise RuntimeError("Frozen specification copy changed")
        (stage / "assets").mkdir()
        shutil.copyfile(ROOT / ".github/docs/extra.css", stage / "assets/extra.css")
        config = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
        config.update(docs_dir=str(stage), site_dir=str(site))
        config_file = Path(temp) / "mkdocs.yml"
        config_file.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        subprocess.run([sys.executable, "-m", "mkdocs", "build", "--strict", "--config-file", str(config_file)], check=True)
    verify_site(site)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    (site / "build-info.json").write_text(json.dumps({"source_commit": commit, "sdk_version": "0.1.0", "frozen_spec_sha256": EXPECTED, "spec_hash_representation": "canonical CRLF", "source_spec_sha256": hashlib.sha256(original_spec).hexdigest()}, indent=2) + "\n", encoding="utf-8")
    environment = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)
    (site / "build-environment.txt").write_text(environment, encoding="utf-8")
    if SPEC.read_bytes() != original_spec:
        raise RuntimeError("Build modified frozen source")


if __name__ == "__main__":
    main()
