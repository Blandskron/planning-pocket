"""Comprobaciones sobre las plantillas que ningún test funcional ve caer.

Las dos que hay aquí son el mismo error cometido dos veces: un comentario
``{# ... #}`` repartido en varias líneas. Django sólo los reconoce en una línea, así
que el resto se renderiza como texto. No rompe nada visiblemente —no hay excepción,
la página responde 200, los tests de vista pasan— pero el texto aparece en pantalla, y
dentro de un contenedor ``display: grid`` el navegador lo envuelve en un ítem anónimo
que añade una fila y descoloca la geometría de alrededor.
"""

from pathlib import Path

import pytest

TEMPLATES = sorted((Path(__file__).resolve().parent.parent / "templates").rglob("*.html"))


def test_there_are_templates_to_check():
    assert TEMPLATES, "no se encontró ninguna plantilla: el test no estaba mirando nada"


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda p: p.name)
def test_short_comments_never_span_several_lines(template):
    """``{#`` tiene que cerrar en su propia línea. Si no, usa ``{% comment %}``."""
    offenders = [
        (number, line.strip()[:70])
        for number, line in enumerate(template.read_text(encoding="utf-8").splitlines(), 1)
        if "{#" in line and "#}" not in line
    ]
    assert not offenders, (
        f"{template.name}: comentario {{# #}} sin cerrar en la misma línea "
        f"(se renderizará como texto): {offenders}"
    )
