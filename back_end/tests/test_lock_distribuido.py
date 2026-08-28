"""app/core/lock_distribuido.py — usado pelo scheduler para os jobs
diários nunca correrem em duplicado com mais de uma instância do
back-end. A ligação ao Redis (ou a ausência dela) é decidida no
IMPORT do módulo, a partir de REDIS_URL — por isso os dois testes
abaixo são mutuamente exclusivos consoante REDIS_URL estava ou não
definida quando a suite arrancou, em vez de dois testes independentes
que passam sempre os dois."""
import pytest

from app.core.lock_distribuido import _redis_cliente, tentar_obter_lock
from tests.conftest import sufixo_unico


@pytest.mark.skipif(_redis_cliente is None, reason="REDIS_URL não definida nesta execução — nada a testar aqui.")
async def test_lock_com_redis_so_a_primeira_instancia_consegue():
    chave = f"teste-lock-{sufixo_unico()}"
    primeira = await tentar_obter_lock(chave, ttl_segundos=5)
    segunda = await tentar_obter_lock(chave, ttl_segundos=5)
    assert primeira is True
    assert segunda is False, "uma segunda tentativa com a mesma chave deveria encontrar o lock já reservado"


@pytest.mark.skipif(_redis_cliente is not None, reason="REDIS_URL definida nesta execução — o fallback não se aplica.")
async def test_lock_sem_redis_e_sempre_obtido_localmente():
    """Sem Redis configurado, assume-se uma única instância — o lock
    nunca bloqueia, para o scheduler continuar a funcionar em
    desenvolvimento local sem precisar de correr Redis."""
    chave = f"teste-lock-sem-redis-{sufixo_unico()}"
    assert await tentar_obter_lock(chave, ttl_segundos=5) is True
    assert await tentar_obter_lock(chave, ttl_segundos=5) is True
