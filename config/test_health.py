# Copyright (c) 2026 Blandskron. All rights reserved.
# Author: Bastian Landskron (Cybersecurity, DevOps & AI)

from django.urls import reverse


def test_health_check(client):
    url = reverse('health_check')
    response = client.get(url)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
