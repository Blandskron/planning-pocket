# Copyright (c) 2024 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

import secrets
import string
import uuid


def generate_public_id(length=9):
    """
    Generate a secure, random, unpredictable alphanumeric ID for public URLs.
    Example: '8FyQx77za'
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_guest_token():
    return uuid.uuid4().hex
