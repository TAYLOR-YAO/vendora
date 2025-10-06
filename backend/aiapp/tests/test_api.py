# This file was auto-generated as a scaffold.
# SAFE to edit. Keep functions/class names if you rely on them across apps.

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_health(client):
    url = reverse('aiapp:health')
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.json().get('status') == 'ok'
