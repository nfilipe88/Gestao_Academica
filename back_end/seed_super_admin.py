"""Cria a conta Super Admin da plataforma (idempotente).

A palavra-passe NUNCA está no código (estava: qualquer pessoa com acesso
ao repositório entraria como Super Admin numa instalação nova). É pedida
sem eco no ecrã, ou lida de SUPER_ADMIN_PASSWORD (para automatizar), e
tem de cumprir as mesmas regras de força do resto da plataforma.

Uso:
    python seed_super_admin.py                      # e-mail por omissão
    python seed_super_admin.py --email admin@dominio.ao
    docker compose exec backend python seed_super_admin.py   (produção)
"""
import argparse
import asyncio
import getpass
import os

from sqlalchemy import select
from app.database.session import AsyncSessionLocalSistema
from app.database.models import Tenant, Usuario
from app.core.security import gerar_hash_senha
from app.core.validacao import validar_forca_senha

# Tenant interno da plataforma — não é uma escola cliente, só existe
# para o(s) login(s) SUPER_ADMIN terem um tenant_id válido (a coluna é
# NOT NULL em Usuario). cruds/admin.py exclui este NIF de
# listar_tenants() e impede alterar o seu status.
NIF_PLATAFORMA = "00000000000"
ADMIN_EMAIL_OMISSAO = "superadmin@gestaoacademica.pt"
_TAMANHO_MINIMO = 12


def _pedir_palavra_passe() -> str:
    senha = os.getenv("SUPER_ADMIN_PASSWORD")
    if not senha:
        senha = getpass.getpass(f"Palavra-passe do Super Admin (mín. {_TAMANHO_MINIMO} caracteres): ")
        if getpass.getpass("Repita a palavra-passe: ") != senha:
            raise SystemExit("As palavras-passe não coincidem.")
    if len(senha) < _TAMANHO_MINIMO:
        raise SystemExit(f"Palavra-passe demasiado curta (mínimo {_TAMANHO_MINIMO} caracteres).")
    try:
        validar_forca_senha(senha)
    except ValueError as erro:
        raise SystemExit(str(erro))
    return senha


async def carregar_super_admin(email: str):
    # AsyncSessionLocalSistema (role app_sistema, bypassrls) — não
    # AsyncSessionLocal (role app_tenant, RLS ativo): este seed corre
    # fora de qualquer pedido HTTP, sem app.current_tenant_id definido
    # na sessão Postgres, por isso o RLS bloquearia tanto o SELECT
    # (devolve sempre "não encontrado", mesmo quando a linha existe)
    # como o INSERT ("new row violates row-level security policy") —
    # ver database/session.py.
    async with AsyncSessionLocalSistema() as db:
        # Idempotente: se já correu antes, não tenta duplicar.
        existente = await db.execute(select(Tenant).where(Tenant.nif == NIF_PLATAFORMA))
        tenant_plataforma = existente.scalars().first()

        if tenant_plataforma:
            usuario_existente = await db.execute(select(Usuario).where(Usuario.email == email))
            if usuario_existente.scalars().first():
                print(f"O Super Admin {email} já existe. Nada a fazer.")
                return

        senha = _pedir_palavra_passe()

        if not tenant_plataforma:
            tenant_plataforma = Tenant(
                nome_fantasia="Gestão Académica — Plataforma",
                nif=NIF_PLATAFORMA,
                status="ATIVO"
            )
            db.add(tenant_plataforma)
            await db.flush()  # obter o id sem ainda fechar a transação

        db.add(Usuario(
            tenant_id=tenant_plataforma.id,
            nome_completo="Super Admin",
            email=email,
            senha_hash=gerar_hash_senha(senha),
            perfil_acesso="SUPER_ADMIN"
        ))
        await db.commit()
        print(f"Super Admin criado: {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", default=ADMIN_EMAIL_OMISSAO)
    asyncio.run(carregar_super_admin(parser.parse_args().email))
