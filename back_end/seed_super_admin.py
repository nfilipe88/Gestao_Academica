import asyncio
from sqlalchemy import select
from app.database.session import AsyncSessionLocalSistema
from app.database.models import Tenant, Usuario
from app.core.security import gerar_hash_senha

# Tenant interno da plataforma — não é uma escola cliente, só existe
# para o(s) login(s) SUPER_ADMIN terem um tenant_id válido (a coluna é
# NOT NULL em Usuario). cruds/admin.py exclui este NIF de
# listar_tenants() e impede alterar o seu status.
NIF_PLATAFORMA = "00000000000"
ADMIN_EMAIL = "superadmin@gestaoacademica.pt"
ADMIN_PASS = "!1qaz2wsX"  # Senha para testarmos — trocar em produção


async def carregar_super_admin():
    # AsyncSessionLocalSistema (role app_sistema, bypassrls) — não
    # AsyncSessionLocal (role app_tenant, RLS ativo): este seed corre
    # fora de qualquer pedido HTTP, sem app.current_tenant_id definido
    # na sessão Postgres, por isso o RLS bloquearia tanto o SELECT
    # (devolve sempre "não encontrado", mesmo quando a linha existe)
    # como o INSERT ("new row violates row-level security policy") —
    # ver database/session.py.
    async with AsyncSessionLocalSistema() as db:
        print("A iniciar seed do Super Admin...")

        # Idempotente: se já correu antes, não tenta duplicar.
        existente = await db.execute(select(Tenant).where(Tenant.nif == NIF_PLATAFORMA))
        tenant_plataforma = existente.scalars().first()

        if tenant_plataforma:
            usuario_existente = await db.execute(
                select(Usuario).where(Usuario.email == ADMIN_EMAIL)
            )
            if usuario_existente.scalars().first():
                print("\n=== Seed do Super Admin já tinha sido aplicado anteriormente. Nada a fazer. ===")
                print(f"Email Login: {ADMIN_EMAIL}")
                print(f"Password: {ADMIN_PASS}")
                print("===================================")
                return
        else:
            tenant_plataforma = Tenant(
                nome_fantasia="Gestão Académica — Plataforma",
                nif=NIF_PLATAFORMA,
                status="ATIVO"
            )
            db.add(tenant_plataforma)
            await db.flush()  # obter o id sem ainda fechar a transação

        novo_super_admin = Usuario(
            tenant_id=tenant_plataforma.id,
            nome_completo="Super Admin",
            email=ADMIN_EMAIL,
            senha_hash=gerar_hash_senha(ADMIN_PASS),
            perfil_acesso="SUPER_ADMIN"
        )
        db.add(novo_super_admin)
        await db.commit()

        print("\n=== Seed do Super Admin concluído com sucesso! ===")
        print(f"Email Login: {ADMIN_EMAIL}")
        print(f"Password: {ADMIN_PASS}")
        print("===================================")


if __name__ == "__main__":
    asyncio.run(carregar_super_admin())
