# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

"""The playful layer: objects people can toss at each other around the table.

This layer is deliberately inert. A throw changes no estimate, blocks no vote and
persists nothing beyond a per-round counter used to rate-limit it. It exists so a
planning session feels like people sitting together instead of a form being filled
in, and it is designed so it cannot turn into pressure:

- The object is identical whether or not the target has voted, so a throw can never
  be read as a signal about someone's vote or their silence.
- Nothing accumulates across rounds. There is no tally of who was hit and no
  ranking of who was slow.
- The catalogue stays soft: food, paper and absurd office objects. Nothing that
  reads as a weapon or as damage.
- Two independent switches can turn it off: the facilitator for the whole room, and
  each person for their own screen.

See docs/DECISIONS.md ADR-005.
"""

THROWABLES = (
    ("tomate", "Tomate"),
    ("papel", "Bola de papel"),
    ("cafe", "Café"),
    ("almohada", "Almohada"),
    ("sello", "Sello aprobado"),
    ("zapatilla", "Zapatilla"),
)

THROWABLE_SLUGS = tuple(slug for slug, _ in THROWABLES)

# One throw every few seconds keeps the table lively without letting anyone carpet
# bomb a neighbour, and the per-round cap stops a whole round becoming a food fight.
THROW_COOLDOWN_SECONDS = 2.5
MAX_THROWS_PER_ROUND = 8
