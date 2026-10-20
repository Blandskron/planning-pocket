# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

"""Las dos barajas de la sala.

Son dos listas cerradas, no una baraja configurable. La razón es la misma que en
``identity.py``: lo que el servidor acepta tiene que caber en una tupla que se pueda
leer de un vistazo. Una baraja escrita a mano obliga a validar longitud, duplicados,
y qué cuenta como numérico para el promedio, a cambio de una libertad que nadie pidió.

La corta es la de por defecto. Trece cartas en un teléfono se recorren de lado, y las
cuatro últimas de Fibonacci sirven para discutir una vez al trimestre; el facilitador
las trae con un interruptor cuando las necesita.

``?`` está en las dos porque «me falta información» es una respuesta de planning, no
una carta de relleno. No entra en el promedio: ``calculate_results`` descarta lo que no
se puede convertir a ``Decimal``.
"""

SHORT_DECK = ("0", "1", "2", "3", "5", "8", "13", "?")
FULL_DECK = ("0", "1", "2", "3", "5", "8", "13", "21", "34", "55", "89", "?", "Coffee")

SHORT_DECK_VALUE = ",".join(SHORT_DECK)
FULL_DECK_VALUE = ",".join(FULL_DECK)


def deck_values(stored):
    """Devuelve las cartas de una baraja almacenada, sin vacíos ni espacios."""
    return tuple(value.strip() for value in (stored or "").split(",") if value.strip())


def is_expanded(stored):
    """¿Esta sala está usando la baraja completa?

    Se deriva de lo guardado en lugar de llevar un booleano aparte, para que no
    puedan contradecirse. Las salas creadas antes de que existiera la baraja corta
    tienen guardada exactamente la completa, así que aparecen ampliadas, que es lo
    que son.
    """
    return deck_values(stored) == FULL_DECK
