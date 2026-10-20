"""El freno de intentos de acceso.

Lo que se protege no es que exista un contador, sino las tres propiedades que lo hacen
útil: que corte, que no delate si la cuenta existe, y que entrar bien lo borre.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse

from accounts import throttling

User = get_user_model()
PASSWORD = "clave-de-prueba-12345"


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestLoginThrottle:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.user = User.objects.create_user(username="victima", password=PASSWORD)
        self.url = reverse("login")

    def fail_once(self, username="victima"):
        return self.client.post(self.url, {"username": username, "password": "mal"})

    @pytest.fixture(autouse=True)
    def _client(self, client):
        self.client = client

    def test_the_counter_cuts_the_attempts_off(self):
        for _ in range(throttling.MAX_ATTEMPTS):
            self.fail_once()
        assert throttling.is_locked_out("victima")

        response = self.fail_once()
        assert b"Demasiados intentos" in response.content

    def test_a_locked_account_refuses_even_the_right_password(self):
        """Si la contraseña correcta pasara, el freno no frenaría nada."""
        for _ in range(throttling.MAX_ATTEMPTS):
            self.fail_once()

        response = self.client.post(self.url, {"username": "victima", "password": PASSWORD})
        assert response.status_code == 200, "entró a pesar del bloqueo"
        assert not response.wsgi_request.user.is_authenticated

    def test_signing_in_clears_the_count(self):
        for _ in range(throttling.MAX_ATTEMPTS - 1):
            self.fail_once()
        assert throttling.attempts_left("victima") == 1

        self.client.post(self.url, {"username": "victima", "password": PASSWORD})
        assert throttling.attempts_left("victima") == throttling.MAX_ATTEMPTS

    def test_the_lockout_does_not_say_whether_the_account_exists(self):
        """Un usuario inventado se bloquea igual, y con el mismo texto."""
        for _ in range(throttling.MAX_ATTEMPTS):
            self.fail_once(username="no-existe")
        inventado = self.fail_once(username="no-existe")

        for _ in range(throttling.MAX_ATTEMPTS):
            self.fail_once()
        real = self.fail_once()

        assert b"Demasiados intentos" in inventado.content
        assert b"Demasiados intentos" in real.content

    def test_each_username_has_its_own_count(self):
        """Bloquear una cuenta no puede dejar fuera al resto de la empresa."""
        otro = User.objects.create_user(username="ajeno", password=PASSWORD)
        for _ in range(throttling.MAX_ATTEMPTS):
            self.fail_once()

        assert throttling.is_locked_out("victima")
        assert not throttling.is_locked_out("ajeno")

        self.client.post(self.url, {"username": "ajeno", "password": PASSWORD})
        assert self.client.session.get("_auth_user_id") == str(otro.pk)


def test_the_window_is_not_renewed_by_further_failures():
    """Si cada fallo reiniciara la ventana, un atacante constante mantendría la cuenta
    bloqueada para siempre."""
    cache.clear()
    throttling.record_failure("alguien")
    primera = cache._expire_info.get(cache.make_key(throttling._key("alguien")))
    for _ in range(5):
        throttling.record_failure("alguien")
    segunda = cache._expire_info.get(cache.make_key(throttling._key("alguien")))
    assert primera == segunda, "la ventana se renovó con cada intento"
