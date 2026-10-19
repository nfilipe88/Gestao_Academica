"""Mapa de Permissões — operações CRUD por perfil e módulo.

PermissaoModulo é o mapa BASE, global (sem tenant_id nem RLS, tal como
PlanoSaaS): os perfis fixos são partilhados por todas as escolas e só o
SUPER_ADMIN o edita. PermissaoModuloEscola guarda as restrições que cada
Gestor faz na própria escola (com RLS) — só existe linha onde a escola
tirou algo ao base.

Desde o bloco D o mapa APLICA-SE (ver app/core/mapa_permissoes.py): cada
pedido só passa se exigir_perfil(...) no código E o mapa base E a
restrição da escola deixarem. O mapa só restringe — nunca dá acima do que
o código permite.
"""
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
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


class PerfilNome(Base):
    """Nome mostrado de cada perfil (ex.: GESTOR → "Diretor Geral"),
    editável pelo Super Admin e igual para toda a plataforma.

    O `codigo` nunca muda: é ele que as permissões reais usam
    (exigir_perfil("GESTOR", ...) em cada rota, Usuario.perfil_acesso).
    Mudar o nome é só o que as pessoas leem — ecrãs, listas, mensagens."""
    __tablename__ = "perfil_nome"

    codigo: Mapped[str] = mapped_column(String(30), primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PermissaoModuloEscola(Base):
    """Restrição do mapa feita por UMA escola (o Gestor) sobre o mapa base
    do Super Admin — só pode tirar, nunca dar (ver
    app/core/mapa_permissoes.py). Sem linha = a escola segue o mapa base."""
    __tablename__ = "permissao_modulo_escola"
    __table_args__ = (UniqueConstraint("tenant_id", "modulo", "perfil", name="uq_permissao_escola_modulo_perfil"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    modulo: Mapped[str] = mapped_column(String(80), nullable=False)
    perfil: Mapped[str] = mapped_column(String(30), nullable=False)
    pode_criar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pode_ler: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pode_atualizar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pode_apagar: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
