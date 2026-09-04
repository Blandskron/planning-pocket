#!/usr/bin/env python3
"""Extrae de CHANGELOG.md las notas de una versión, y comprueba que existan.

Vive como archivo y no como una línea dentro del workflow a propósito: la primera versión
metía un `awk` con expresiones regulares escapadas dentro de un bloque YAML, y para cuando
la cadena llegaba a awk le faltaban las barras invertidas. El fallo sólo se veía al empujar
un tag, que es el peor momento posible para descubrirlo. Aquí se puede ejecutar en local:

    python .github/scripts/release_notes.py 1.0.0
    python .github/scripts/release_notes.py 1.0.0 --check
"""

import argparse
import pathlib
import sys


def extract(changelog: str, version: str) -> str:
    """Devuelve todo lo que hay entre la cabecera de `version` y la siguiente cabecera."""
    header = "## [" + version + "]"
    collected: list[str] = []
    found = False
    for line in changelog.splitlines():
        if line.startswith(header):
            found = True
            continue
        if found and line.startswith("## ["):
            break
        if found:
            collected.append(line)
    if not found:
        return ""
    return "\n".join(collected).strip()


def main() -> int:
    # El changelog está en español y las notas van tal cual a la GitHub Release.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Versión sin la v inicial, por ejemplo 1.0.0")
    parser.add_argument(
        "--changelog", default="CHANGELOG.md", type=pathlib.Path, help="Ruta del changelog"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="No imprime nada: sólo sale con 0 si la sección existe y tiene contenido.",
    )
    args = parser.parse_args()

    notes = extract(args.changelog.read_text(encoding="utf-8"), args.version)
    if not notes:
        print(
            "::error::" + str(args.changelog) + " no tiene una sección '## ["
            + args.version + "]' con contenido",
            file=sys.stderr,
        )
        return 1
    if not args.check:
        print(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
