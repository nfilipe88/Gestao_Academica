"""
Verificação em dois passos por e-mail (opcional, ligada pelo próprio no
Perfil — ver Usuario.dois_fatores_ativo e
models_usuarios.py::DesafioDoisFatores).

Um "desafio" é um pedido de código: o cliente recebe só um token
aleatório (o desafio) e a pessoa recebe o código de 6 dígitos por
e-mail; só com os dois se conclui o passo. As funções recebem a sessão
de quem chama: o login usa app_sistema (pré-autenticado, ver
cruds/auth.py), o Perfil usa a sessão normal da escola (RLS).
"""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import eventos_seguranca, fila_notificacoes
from app.core.email import enviar_email, escapar, template_base
from app.core.security import SECRET_KEY
from app.database.models import Usuario
from app.database.models_usuarios import DesafioDoisFatores

LOGIN = "LOGIN"
ATIVAR = "ATIVAR"

VALIDADE_MINUTOS = 10
_MAX_TENTATIVAS = 5
_MAX_REENVIOS = 3

_DESAFIO_INVALIDO = "Este código expirou ou já não é válido. Peça um novo código."


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def _hash_codigo(desafio_id: uuid.UUID, codigo: str) -> str:
    # HMAC com a chave do servidor: um dump da tabela não chega para
    # testar o milhão de códigos possíveis offline.
    return hmac.new(SECRET_KEY.encode(), f"{desafio_id}:{codigo}".encode(), hashlib.sha256).hexdigest()


def _novo_codigo() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def mascarar_email(email: str) -> str:
    """"gestor@escola.pt" → "g****r@escola.pt" — confirma o destino sem o revelar a quem só sabe a palavra-passe."""
    local, _, dominio = email.partition("@")
    if len(local) <= 2:
        return f"{local[:1]}***@{dominio}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{dominio}"


async def _enviar_codigo(usuario: Usuario, codigo: str, finalidade: str) -> None:
    if finalidade == LOGIN:
        assunto = "Código de acesso à sua conta"
        intro = "Use este código para concluir o início de sessão:"
    else:
        assunto = "Código para ativar a verificação em dois passos"
        intro = "Use este código para confirmar a ativação da verificação em dois passos:"
    await fila_notificacoes.agendar_email(
        enviar_email, destinatario=usuario.email, assunto=assunto,
        corpo_html=template_base(
            assunto,
            f"""
            <p>Olá {escapar(usuario.nome_completo)},</p>
            <p>{intro}</p>
            <p style="font-size:28px;font-weight:bold;letter-spacing:6px;">{codigo}</p>
            <p>O código expira em {VALIDADE_MINUTOS} minutos. Se não foi você a pedi-lo, alguém sabe a sua
            palavra-passe: mude-a imediatamente no seu Perfil e contacte a direção da escola.</p>
            """
        )
    )


async def criar_desafio(db: AsyncSession, usuario: Usuario, finalidade: str) -> str:
    """Gera e envia um código novo; invalida os desafios anteriores
    ainda pendentes da mesma pessoa e finalidade. Devolve o desafio."""
    await db.execute(
        update(DesafioDoisFatores)
        .where(
            DesafioDoisFatores.usuario_id == usuario.id, DesafioDoisFatores.finalidade == finalidade,
            DesafioDoisFatores.usado.is_(False),
        )
        .values(usado=True)
    )
    desafio_bruto = secrets.token_urlsafe(32)
    codigo = _novo_codigo()
    registo = DesafioDoisFatores(
        id=uuid.uuid4(), tenant_id=usuario.tenant_id, usuario_id=usuario.id, finalidade=finalidade,
        desafio_hash=_hash(desafio_bruto),
        expira_em=datetime.now(timezone.utc) + timedelta(minutes=VALIDADE_MINUTOS),
    )
    registo.codigo_hash = _hash_codigo(registo.id, codigo)
    db.add(registo)
    await db.commit()
    await _enviar_codigo(usuario, codigo, finalidade)
    return desafio_bruto


async def _obter_desafio_valido(db: AsyncSession, desafio_bruto: str, finalidade: str) -> DesafioDoisFatores:
    registo = (await db.execute(
        select(DesafioDoisFatores).where(DesafioDoisFatores.desafio_hash == _hash(desafio_bruto))
    )).scalars().first()
    if (
        not registo or registo.usado or registo.finalidade != finalidade
        or registo.expira_em.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc)
        or registo.tentativas >= _MAX_TENTATIVAS
    ):
        raise HTTPException(status_code=400, detail=_DESAFIO_INVALIDO)
    return registo


async def validar_codigo(db: AsyncSession, desafio_bruto: str, codigo: str, finalidade: str) -> uuid.UUID:
    """Devolve o usuario_id se o código estiver certo (o desafio deixa de
    servir). Cada erro conta; ao 5.º o desafio morre e é preciso pedir
    outro código (o que exige de novo a palavra-passe, no login)."""
    registo = await _obter_desafio_valido(db, desafio_bruto, finalidade)
    if not hmac.compare_digest(registo.codigo_hash, _hash_codigo(registo.id, codigo.strip())):
        registo.tentativas += 1
        restantes = _MAX_TENTATIVAS - registo.tentativas
        if restantes <= 0:
            registo.usado = True
        await db.commit()
        email = (await db.execute(select(Usuario.email).where(Usuario.id == registo.usuario_id))).scalar_one_or_none()
        await eventos_seguranca.registar(
            eventos_seguranca.DOIS_FATORES_FALHADO,
            eventos_seguranca.MEDIA if restantes <= 0 else eventos_seguranca.BAIXA,
            "Código da verificação em dois passos errado"
            + (" pela 5.ª vez — código anulado." if restantes <= 0 else f" ({registo.tentativas}.ª tentativa)."),
            email=email, tenant_id=registo.tenant_id,
        )
        if restantes <= 0:
            raise HTTPException(status_code=400, detail="Código incorreto demasiadas vezes. Volte a iniciar sessão.")
        raise HTTPException(status_code=400, detail=f"Código incorreto. Restam {restantes} tentativa(s).")
    registo.usado = True
    await db.commit()
    return registo.usuario_id


async def reenviar_codigo(db: AsyncSession, desafio_bruto: str, finalidade: str) -> None:
    """Novo código no mesmo desafio (o anterior deixa de valer). As
    tentativas falhadas NÃO voltam a zero — reenviar não dá mais
    hipóteses de adivinhar."""
    registo = await _obter_desafio_valido(db, desafio_bruto, finalidade)
    if registo.reenvios >= _MAX_REENVIOS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Já pediu demasiados códigos. Volte a iniciar sessão para receber um novo."
        )
    usuario = (await db.execute(select(Usuario).where(Usuario.id == registo.usuario_id))).scalars().first()
    codigo = _novo_codigo()
    registo.codigo_hash = _hash_codigo(registo.id, codigo)
    registo.reenvios += 1
    registo.expira_em = datetime.now(timezone.utc) + timedelta(minutes=VALIDADE_MINUTOS)
    await db.commit()
    await _enviar_codigo(usuario, codigo, finalidade)
