import asyncio
import uuid
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import Tenant, Usuario
from app.core.security import gerar_hash_senha

NIF_SEED = "123456789"
ADMIN_EMAIL = "admin@escola.pt"
ADMIN_PASS = "!1qaz2wsX"  # Senha para testarmos

async def carregar_dados_iniciais():
    async with AsyncSessionLocal() as db:
        print("A iniciar processo de Seed...")

        # Idempotente: se já correu antes, não tenta duplicar (evita
        # rebentar com UniqueViolationError no nif/email).
        existente = await db.execute(select(Tenant).where(Tenant.nif == NIF_SEED))
        if existente.scalars().first():
            print("\n=== Seed já tinha sido aplicado anteriormente. Nada a fazer. ===")
            print(f"Email Login: {ADMIN_EMAIL}")
            print(f"Password: {ADMIN_PASS}")
            print("===================================")
            return

        # 1. Criar a Instituição (Tenant)
        tenant_id = uuid.uuid4()
        nova_escola = Tenant(
            id=tenant_id,
            nome_fantasia="Escola Secundária Central",
            nif=NIF_SEED,
            status="ATIVO"
        )
        db.add(nova_escola)

        # 2. Criar o Utilizador Gestor / Admin
        novo_admin = Usuario(
            tenant_id=tenant_id,
            nome_completo="Diretor Silva",
            email=ADMIN_EMAIL,
            senha_hash=gerar_hash_senha(ADMIN_PASS),
            perfil_acesso="GESTOR"
        )
        db.add(novo_admin)

        # Guardar na BD
        await db.commit()

        print("\n=== Seed Concluído com Sucesso! ===")
        print(f"Escola Criada: {nova_escola.nome_fantasia}")
        print(f"Email Login: {ADMIN_EMAIL}")
        print(f"Password: {ADMIN_PASS}")
        print("===================================")

if __name__ == "__main__":
    asyncio.run(carregar_dados_iniciais())