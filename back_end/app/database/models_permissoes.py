"""Mapa de Permissões — matriz global (não por tenant) de operações CRUD
por perfil e módulo.

Global de propósito: os cinco perfis fixos (SUPER_ADMIN, GESTOR,
SECRETARIA, PROFESSOR, ALUNO_RESPONSAVEL) são partilhados por todas as
escolas da plataforma — não há "o mapa da escola X", há um só mapa. Por
isso, tal como PlanoSaaS (ver models_billing.py), esta tabela não tem
tenant_id nem RLS.

IMPORTANTE — isto é um mapa de referência/documentação editável pelo
SUPER_ADMIN e pelo GESTOR (ver permissoes.component.html: "Cada pedido
ao back-end passa por uma verificação de perfil... o front-end só
reflete essa regra, nunca decide sozinho"). Editar uma célula aqui
NÃO altera o RBAC real da API — esse continua a viver, sozinho, nos
decorators exigir_perfil(...) de cada endpoint. Este mapa existe para
documentar esse RBAC de forma legível e para deixar registo de
decisões/exceções, não para o aplicar.
"""
import uuid

from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class PermissaoModulo(Base):
    __tablename__ = "permissao_modulo"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # "ordem" fixa a ordem das linhas na tabela (a ordem de inserção do
    # Postgres não é garantida sem ORDER BY) — replica a ordem do antigo
    # array MODULOS hardcoded no frontend.
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    modulo: Mapped[str] = mapped_column(String(80), nullable=False)

    # 'super_admin' | 'gestor' | 'secretaria' | 'professor' | 'aluno_responsavel'
    perfil: Mapped[str] = mapped_column(String(30), nullable=False)

    pode_criar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pode_ler: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pode_atualizar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pode_apagar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("modulo", "perfil", name="uq_permissao_modulo_perfil"),
    )
