# Installation Guide

## Requirements

- Python **≥ 3.10**
- No mandatory third-party runtime dependencies for W2 Core
- Optional for development: `pytest`, `build`, `wheel`

## Editable install (developers)

```powershell
cd saxil-core
python -m pip install -e ".[dev]"
```

## Wheel / sdist

From the extracted package directory (for example after unpacking the sdist):

```powershell
cd saxil-core
python -m pip install build
python -m build
python -m pip install dist\saxil_core-*.whl
```

Offline example (wheels already present locally):

```powershell
python -m pip install --no-index --find-links=dist saxil-core
```

## Verify

```powershell
python -c "import saxil_core; print(saxil_core.__version__); print(saxil_core.get_version_info())"
saxil version
```

## Notes

- Publishing to GitHub or PyPI requires a separate explicit owner GO; Apache-2.0 approval alone is not a publish grant.
- Model weights are **not** included in this package.
- Apache-2.0 `LICENSE` and `NOTICE` are part of the public package when applied by an authorized root writer.
