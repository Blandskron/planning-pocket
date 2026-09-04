#!/usr/bin/env python3
"""Imprime la versión declarada en pyproject.toml.

Es un archivo y no un `python -c` dentro del YAML por la misma razón que
release_notes.py: lo que se puede ejecutar en local antes de empujar un tag, se arregla
antes de empujar un tag.
"""

import pathlib
import tomllib

data = tomllib.loads(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))
print(data["project"]["version"])
