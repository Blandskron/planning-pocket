# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

"""Cosmetic table identity: the face, pet and colour a participant is drawn with.

None of this is secret. Identity is broadcast while voting is still open so people
can find each other around the ring; it carries no information about how anyone
voted, and the privacy rule in ``PokerConsumer._participant_state`` is untouched.

Values are validated against the closed tuples below. Anything unset falls back to
a stable derivation from the participant's own token, so rows that predate these
fields still render a recognisable seat without a data migration.
"""

from hashlib import blake2b

FACES = (
    ("sereno", "Sereno"),
    ("contento", "Contento"),
    ("pillo", "Pillo"),
    ("dormilon", "Dormilón"),
)

PETS = (
    ("gato", "Gato"),
    ("perro", "Perro"),
    ("axolote", "Axolote"),
    ("capibara", "Capibara"),
    ("dragon", "Dragón"),
    ("rana", "Rana"),
)

COLOR_COUNT = 7

FACE_SLUGS = tuple(slug for slug, _ in FACES)
PET_SLUGS = tuple(slug for slug, _ in PETS)
COLOR_CHOICES = tuple((index, f"Color {index + 1}") for index in range(COLOR_COUNT))


def derive_identity(seed):
    """Return a stable ``(face, pet, colour)`` triple for a seed value.

    The same seed always produces the same triple, so a participant who never
    picked anything keeps the same seat identity across reconnections.
    """
    digest = blake2b(str(seed or "").encode("utf-8"), digest_size=6).digest()
    return (
        FACE_SLUGS[digest[0] % len(FACE_SLUGS)],
        PET_SLUGS[digest[1] % len(PET_SLUGS)],
        digest[2] % COLOR_COUNT,
    )
