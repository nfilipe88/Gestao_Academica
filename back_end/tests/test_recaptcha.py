"""Verificação de Google reCAPTCHA v3 (ver app/core/recaptcha.py) — sem
rede real para a Google: o cliente HTTP é substituído por um duplo de
teste, já que não há biblioteca de mock de HTTP instalada neste projeto."""
import httpx

from app.core import recaptcha


class _RespostaFalsa:
    def __init__(self, corpo: dict):
        self._corpo = corpo

    def json(self):
        return self._corpo


class _ClienteFalso:
    def __init__(self, corpo: dict | None = None, excecao: Exception | None = None):
        self._corpo = corpo
        self._excecao = excecao

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        if self._excecao:
            raise self._excecao
        return _RespostaFalsa(self._corpo)


async def test_sem_secret_key_ignora_verificacao(monkeypatch):
    """Ambiente de dev/testes, sem RECAPTCHA_SECRET_KEY configurada —
    nunca deve bloquear, com ou sem token."""
    monkeypatch.setattr(recaptcha, "RECAPTCHA_SECRET_KEY", None)
    assert await recaptcha.token_e_valido(None) is True
    assert await recaptcha.token_e_valido("qualquer-coisa") is True


async def test_com_secret_key_recusa_pedido_sem_token(monkeypatch):
    monkeypatch.setattr(recaptcha, "RECAPTCHA_SECRET_KEY", "chave-de-teste")
    assert await recaptcha.token_e_valido(None) is False


async def test_score_abaixo_do_limiar_e_recusado(monkeypatch):
    monkeypatch.setattr(recaptcha, "RECAPTCHA_SECRET_KEY", "chave-de-teste")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _ClienteFalso({"success": True, "score": 0.2}))
    assert await recaptcha.token_e_valido("token-suspeito") is False


async def test_score_acima_do_limiar_e_aceite(monkeypatch):
    monkeypatch.setattr(recaptcha, "RECAPTCHA_SECRET_KEY", "chave-de-teste")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _ClienteFalso({"success": True, "score": 0.9}))
    assert await recaptcha.token_e_valido("token-humano") is True


async def test_success_false_e_recusado_mesmo_com_score_alto(monkeypatch):
    """A Google pode devolver score alto com success=False (ex.: token
    expirado/reutilizado) — o score sozinho nunca chega."""
    monkeypatch.setattr(recaptcha, "RECAPTCHA_SECRET_KEY", "chave-de-teste")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _ClienteFalso({"success": False, "score": 0.9}))
    assert await recaptcha.token_e_valido("token-invalido") is False


async def test_falha_de_rede_falha_aberta(monkeypatch):
    """A Google em baixo não pode derrubar o registo/lead em si — o
    rate limiting continua a cobrir o essencial do abuso."""
    monkeypatch.setattr(recaptcha, "RECAPTCHA_SECRET_KEY", "chave-de-teste")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _ClienteFalso(excecao=httpx.ConnectError("sem rede")))
    assert await recaptcha.token_e_valido("token-qualquer") is True
