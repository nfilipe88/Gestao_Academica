"""
Gestão de Acessos (RBAC) — Núcleo Multi-Tenant.

Toda a lógica aqui é parametrizada por tenant_id (o alvo), não pelo
tenant de quem está a executar a ação — é o que permite reutilizar as
mesmas funções tanto para o Gestor (só a própria escola, tenant_id vem
do token) como para o Super Admin (qualquer escola, tenant_id vem do
path da URL). Ver app/api/v1/usuarios.py (Gestor) e
app/api/v1/admin.py (Super Admin).

Duas restrições deliberadas, para não comprometer a integridade de
outros módulos:
  - Mudança de perfil só é permitida entre GESTOR e SECRETARIA — são os
    dois únicos perfis que são "só" um Usuario, sem tabela satélite
    (Professor tem alocações/Diário; Aluno/Responsavel têm o seu
    próprio fluxo em cruds/alunos.py::_criar_acesso). Converter de/para
    Professor ou Aluno/Responsavel deixaria dados órfãos.
  - Suspensão (ativo) aplica-se a qualquer perfil, porque é reversível
    e não mexe em nenhuma tabela satélite.
"""
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Usuario
from app.database.models_usuarios import UsuarioAuditoria
from app.core.security import gerar_hash_senha
from app.core.paginacao import DEFAULT_PAGE_SIZE, paginar, paginar_linhas
from app.schemas.usuarios import PerfilAcessoUpdate, SecretariaCreate

# Perfis de staff "puros" — sem tabela satélite (Professor/Aluno/Responsavel
# ficam de fora, ver docstring do módulo).
PERFIS_SEM_SUBTABELA = {"GESTOR", "SECRETARIA"}

# Perfis de staff mostrados na listagem de Gestão de Acessos — Aluno/
# Responsavel continuam geridos em Alunos (cruds/alunos.py), não aqui.
PERFIS_STAFF = {"GESTOR", "SECRETARIA", "PROFESSOR"}


async def _obter_usuario_no_tenant(db: AsyncSession, tenant_id, usuario_id: uuid.UUID) -> Usuario:
    usuario = (await db.execute(
        select(Usuario).where(Usuario.id == usuario_id, Usuario.tenant_id == tenant_id)
    )).scalars().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado nesta instituição.")
    return usuario


async def _contar_outros_gestores_ativos(db: AsyncSession, tenant_id, excluir_usuario_id: uuid.UUID) -> int:
    gestores = (await db.execute(
        select(Usuario.id).where(
            Usuario.tenant_id == tenant_id, Usuario.perfil_acesso == "GESTOR",
            Usuario.ativo == True, Usuario.id != excluir_usuario_id  # noqa: E712
        )
    )).scalars().all()
    return len(gestores)


async def _registar_auditoria(
    db: AsyncSession, tenant_id, usuario_alvo_id: uuid.UUID, autor_id: uuid.UUID | None, acao: str,
    perfil_anterior: str | None = None, perfil_novo: str | None = None, detalhe: str | None = None
) -> None:
    db.add(UsuarioAuditoria(
        tenant_id=tenant_id, usuario_alvo_id=usuario_alvo_id, autor_id=autor_id, acao=acao,
        perfil_anterior=perfil_anterior, perfil_novo=perfil_novo, detalhe=detalhe
    ))


async def listar_usuarios(db: AsyncSession, tenant_id, page: int, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    """Staff da escola (GESTOR/SECRETARIA/PROFESSOR) — Aluno/Responsavel ficam em Alunos."""
    query = (
        select(Usuario)
        .where(Usuario.tenant_id == tenant_id, Usuario.perfil_acesso.in_(PERFIS_STAFF))
        .order_by(Usuario.nome_completo)
    )
    pagina = await paginar(db, query, page, page_size)
    # Serialização explícita — nunca devolver o Usuario tal como veio da
    # base de dados: tem senha_hash, que não pode sair da API de forma nenhuma.
    pagina["items"] = [
        {
            "id": u.id,
            "nome_completo": u.nome_completo,
            "email": u.email,
            "perfil_acesso": u.perfil_acesso,
            "ativo": u.ativo,
            "data_criacao": u.data_criacao,
        }
        for u in pagina["items"]
    ]
    return pagina


async def criar_secretaria(db: AsyncSession, tenant_id, dados: SecretariaCreate, autor_id: uuid.UUID | None) -> Usuario:
    """Não existia nenhuma forma de criar uma conta de Secretaria antes desta função — só Professor e Portal tinham fluxo próprio."""
    email_existente = (await db.execute(select(Usuario).where(Usuario.email == dados.email))).scalars().first()
    if email_existente:
        raise HTTPException(status_code=400, detail="Este email já está em uso.")

    novo = Usuario(
        tenant_id=tenant_id,
        nome_completo=dados.nome_completo,
        email=dados.email,
        senha_hash=gerar_hash_senha(dados.palavra_passe),
        perfil_acesso="SECRETARIA",
        ativo=True,
    )
    db.add(novo)
    await db.flush()
    await _registar_auditoria(db, tenant_id, novo.id, autor_id, acao="CRIACAO_SECRETARIA", perfil_novo="SECRETARIA")
    await db.commit()
    await db.refresh(novo)
    return novo


async def alterar_perfil(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, dados: PerfilAcessoUpdate, autor_id: uuid.UUID | None) -> Usuario:
    usuario = await _obter_usuario_no_tenant(db, tenant_id, usuario_id)

    if dados.perfil_acesso not in PERFIS_SEM_SUBTABELA:
        raise HTTPException(status_code=400, detail='Só é possível atribuir o perfil "GESTOR" ou "SECRETARIA" por aqui.')
    if usuario.perfil_acesso not in PERFIS_SEM_SUBTABELA:
        raise HTTPException(
            status_code=400,
            detail=f'Não é possível mudar o perfil de um utilizador "{usuario.perfil_acesso}" por aqui — '
                   f"tem dados associados (alocações, matrícula) que dependem do perfil atual."
        )

    perfil_anterior = usuario.perfil_acesso
    if perfil_anterior == dados.perfil_acesso:
        return usuario  # nada a fazer, idempotente

    if perfil_anterior == "GESTOR" and await _contar_outros_gestores_ativos(db, tenant_id, usuario_id) == 0:
        raise HTTPException(status_code=400, detail="Esta é a última conta de Gestor ativa da escola — não pode ficar sem nenhuma.")

    usuario.perfil_acesso = dados.perfil_acesso
    await _registar_auditoria(
        db, tenant_id, usuario.id, autor_id, acao="MUDANCA_PERFIL",
        perfil_anterior=perfil_anterior, perfil_novo=dados.perfil_acesso
    )
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def alterar_estado_ativo(db: AsyncSession, tenant_id, usuario_id: uuid.UUID, ativo: bool, autor_id: uuid.UUID | None) -> Usuario:
    usuario = await _obter_usuario_no_tenant(db, tenant_id, usuario_id)

    if not ativo and autor_id is not None and usuario.id == autor_id:
        raise HTTPException(status_code=400, detail="Não pode suspender a sua própria conta.")
    if usuario.ativo == ativo:
        return usuario  # idempotente

    if not ativo and usuario.perfil_acesso == "GESTOR" and await _contar_outros_gestores_ativos(db, tenant_id, usuario_id) == 0:
        raise HTTPException(status_code=400, detail="Esta é a última conta de Gestor ativa da escola — não pode ficar sem nenhuma.")

    usuario.ativo = ativo
    await _registar_auditoria(
        db, tenant_id, usuario.id, autor_id, acao="REATIVACAO" if ativo else "SUSPENSAO",
        detalhe=f'Perfil no momento da ação: {usuario.perfil_acesso}.'
    )
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def listar_auditoria(db: AsyncSession, tenant_id, page: int, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    query = (
        select(UsuarioAuditoria, Usuario.nome_completo)
        .join(Usuario, Usuario.id == UsuarioAuditoria.usuario_alvo_id)
        .where(UsuarioAuditoria.tenant_id == tenant_id)
        .order_by(UsuarioAuditoria.data_acao.desc())
    )
    pagina = await paginar_linhas(db, query, page, page_size)

    autor_ids = {linha[0].autor_id for linha in pagina["items"] if linha[0].autor_id}
    nomes_autores = {}
    if autor_ids:
        nomes_autores = dict((await db.execute(
            select(Usuario.id, Usuario.nome_completo).where(Usuario.id.in_(autor_ids))
        )).all())

    pagina["items"] = [
        {
            "id": registo.id,
            "usuario_alvo_id": registo.usuario_alvo_id,
            "nome_alvo": nome_alvo,
            "nome_autor": nomes_autores.get(registo.autor_id),
            "acao": registo.acao,
            "perfil_anterior": registo.perfil_anterior,
            "perfil_novo": registo.perfil_novo,
            "detalhe": registo.detalhe,
            "data_acao": registo.data_acao,
        }
        for registo, nome_alvo in pagina["items"]
    ]
    return pagina
