# Installation guide

## Requirements

- Python **3.10 or later**.
- No mandatory third-party runtime dependencies for W2 Core.
- Public CI covers Linux and Windows with Python 3.10–3.13; other versions and
  platforms are not implied to be verified by the minimum-version declaration.

## Install version 0.1.0

Create a virtual environment:

```sh
python -m venv .venv
```

Activate it in PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Or in a POSIX shell:

```sh
. .venv/bin/activate
```

Install the released package:

```sh
python -m pip install saxil-core==0.1.0
python -m pip check
```

## Verify

```sh
python -c "import saxil_core; print(saxil_core.__version__); print(saxil_core.get_version_info())"
python -m saxil_core version
```

The software version should be `0.1.0`, protocol version `2`, and codec profile
`W2-v1`. The `saxil` entry point provides the same CLI as `python -m saxil_core`.
Continue with the [README roundtrip](../README.md#try-a-canonical-roundtrip) or
the [quick start](QUICKSTART.md).

## Offline installation

On a machine with network access, obtain the published wheel from
[PyPI](https://pypi.org/project/saxil-core/0.1.0/#files) or the
[official release](https://github.com/SayaOpenTech/saxil-core/releases/tag/v0.1.0).
Verify the wheel's SHA-256 against the published metadata/SHA256SUMS and transfer
it to the offline machine. Place it in a local `wheels` directory, then run:

```sh
python -m pip install --no-index --find-links=wheels saxil-core==0.1.0
```

W2 encoding and decoding operate locally after installation. Model weights and
online inference services are not needed. See [offline usage](OFFLINE_USAGE_EXAMPLE.md).

## Contributor checkout

For development on a cloned public repository, install the checkout and optional
test dependency instead of the published wheel:

```sh
python -m pip install -e ".[dev]"
python -m pytest tests -q
```

See [CONTRIBUTING.md](../CONTRIBUTING.md). A source checkout can differ from the
released 0.1.0 distribution. Installing or testing a checkout does not authorize a
release, a PyPI upload, or replacement of existing release artifacts.

The published package includes Apache-2.0 [LICENSE](../LICENSE) and
[NOTICE](../NOTICE). Model weights are not included.
