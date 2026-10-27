# Documentation website maintenance

The public site is [sayaopentech.github.io/saxil-core](https://sayaopentech.github.io/saxil-core/).

## Choice and scope

MkDocs 1.6.1 is suitable for the existing Markdown documentation: navigation,
local search, fenced code, reference pages and strict link diagnostics need no
SDK import or research dependencies. The built-in theme avoids a separate theme
dependency. Documentation tooling is separate from `pyproject.toml`.

The build copies an allowlist of public Markdown, specification JSON and example
source into a temporary tree, preserving repository-relative links. It checks the
frozen specification's approved SHA-256 before and after the build and copies it
without changing source bytes. Existing normative source is never rewritten.

## Reproduce the build

From a public checkout in a separate virtual environment:

```sh
python -m pip install -r requirements-docs.txt
python .github/docs/build_docs.py
python -m http.server 8000 --directory site --bind 127.0.0.1
```

Open `http://127.0.0.1:8000/`. The script runs `mkdocs build --strict`, validates
local generated HTML/asset links, and writes `site/build-info.json` and
`site/build-environment.txt`. The first identifies the source revision and frozen
specification; the second records resolved build dependencies. MkDocs is pinned,
but transitive dependencies are resolved at install time: this is a reproducible
procedure, not a claim of bit-for-bit identical builds across environments.

## GitHub Pages deployment

The `Documentation site` workflow builds PRs with read-only repository permission.
Only upstream `main` push/manual runs upload and deploy the validated site.
The separate deployment job requests Pages/OIDC permissions and uses the
`github-pages` environment. That environment is restricted to branch `main`.
No PyPI permission, token or publishing environment is involved.

Initial owner-authorized administration creates a Pages site with
`build_type=workflow` and a `github-pages` environment with a custom `main` branch
policy. There is no custom domain, DNS edit or repository source branch used as
a generated-site store. Main PR/CI rules and `pypi` remain unchanged.

After a merge, inspect the workflow run, deployment result and public URL.
`build-info.json` should identify the deployed main commit. A PR build never
publishes. A successful deployment does not test every external link or prove
that the codec is secure.

## Rollback

Revert faulty source through a reviewed PR, let its strict build pass, then
redeploy from main. Do not roll back by weakening main rules or deploying an
unreviewed branch. Baseline Pages/environment state before this task was absent;
an owner-requested administrative rollback can remove only this new Pages site
and its dedicated environment after retaining source and deployment evidence.
No released package, tag or PyPI artifact is changed by a docs deployment.
