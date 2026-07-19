"""Setuptools compatibility shim; project metadata lives in pyproject.toml."""
from pathlib import Path
from runpy import run_path
from setuptools import setup  # type: ignore[import-untyped]

cmdclass = run_path(str(Path(__file__).parent / "scripts" / "packaging_hooks.py"))["cmdclass"]
setup(cmdclass=cmdclass)
