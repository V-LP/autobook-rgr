"""Sphinx configuration for the AutoBook API reference."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

project = "AutoBook SDD"
copyright = "2026, AutoBook SDD"
author = "AutoBook SDD"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

root_doc = "index"
language = "uk"
exclude_patterns = ["_build"]
html_theme = "sphinx_rtd_theme"
html_static_path = []
