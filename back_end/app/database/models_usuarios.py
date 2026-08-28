import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models import Base


class UsuarioAuditoria(Base):
    """
    Rasto de ações sensíveis de RBAC sobre uma conta (Núcleo Multi-Tenant):
    criação de conta de Secretaria, mudança de perfil_acesso, suspensão
    e reativação — quem fez, quando, e o antes/depois. Gerada por
    cruds/usuarios.py, nunca escrita diretamente por um endpoint.

    Escrita tanto pelo Gestor (gere o pessoal da própria escola) como
    pelo Super Admin (gere qualquer escola) — por isso tenant_id é
    sempre o do UTILIZADOR ALVO da ação, não o de quem a executou (o
    Super Admin não tem tenant_id de escola nenhuma).
    """
    __tablename__ = "usuario_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_alvo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    # SET NULL (não CASCADE): o autor pode ser de outro tenant (Super
    # Admin) e o registo de auditoria deve sobreviver mesmo que a conta
    # de quem executou a ação deixe de existir.
    autor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True)

    # CRIACAO_SECRETARIA, MUDANCA_PERFIL, SUSPENSAO, REATIVACAO
    acao: Mapped[str] = mapped_column(String(30), nullable=False)
    perfil_anterior: Mapped[str | None] = mapped_column(String(50), nullable=True)
    perfil_novo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detalhe: Mapped[str | None] = mapped_column(Text, nullable=True)

    data_acao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class PasswordResetToken(Base):
    """
    Token de recuperação de palavra-passe (fluxo "esqueci-me da senha",
    sempre pré-autenticado — ver cruds/auth.py::solicitar_redefinicao_senha
    e redefinir_senha, que usam a sessão app_sistema pela mesma razão do
    login/registo: procurar por email não sabe a priori o tenant).

    Só o HASH do token (sha256) fica gravado — o token em texto limpo só
    existe no e-mail enviado ao utilizador, nunca na base de dados, o
    mesmo princípio já aplicado a Usuario.senha_hash. `usado` impede
    reutilização do link mesmo dentro da janela de validade (ex.: o
    e-mail foi reencaminhado ou aberto duas vezes).
    """
    __tablename__ = "password_reset_token"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)

    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class RefreshToken(Base):
    """
    Refresh token (Fase 5 — segurança de sessão): o access token (JWT,
    ver app/core/security.py) passou a durar só ~20 min — sem isto, a
    sessão do utilizador morreria a cada 20 min de inatividade. Este
    token, muito mais duradouro (dias), vive na BD e por isso é
    revogável de verdade (ao contrário do JWT, que é stateless) — é
    isso que faz o "Sair do Sistema"/logout ter efeito real no back-end,
    e não só apagar o token do browser.

    Rotação a cada uso (ver POST /auth/refresh em app/api/v1/auth.py):
    cada pedido de refresh marca ESTE token como usado e cria um novo —
    um token de refresh nunca é reutilizável, o que também serve de
    deteção básica de roubo (um token de refresh já usado a aparecer de
    novo só pode significar que alguém copiou o token antigo).

    Só o HASH (sha256) fica gravado, mesmo princípio do
    PasswordResetToken acima.
    """
    __tablename__ = "refresh_token"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)

    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revogado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))


class LoginHistorico(Base):
    """
    Registo de logins bem-sucedidos (Fase 5) — usado para alertar por
    e-mail quando um login acontece a partir de um IP nunca visto antes
    para aquele utilizador (ver cruds/auth.py::autenticar). Não é uma
    proteção por si só (um atacante com a palavra-passe continua a
    conseguir entrar), é um sinal cedo: o dono da conta fica a saber
    que algo aconteceu a tempo de mudar a palavra-passe.
    """
    __tablename__ = "login_historico"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)

    ip: Mapped[str] = mapped_column(String(45), nullable=False)  # IPv6 até 45 chars
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
