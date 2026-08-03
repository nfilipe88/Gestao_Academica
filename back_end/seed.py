import asyncio
import uuid
# from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import AsyncSessionLocal
from app.database.models import Tenant, Usuario
from app.core.security import gerar_hash_senha

async def carregar_dados_iniciais():
    async with AsyncSessionLocal() as db:
        print("A iniciar processo de Seed...")
        
        # 1. Criar a Instituição (Tenant)
        tenant_id = uuid.uuid4()
        nova_escola = Tenant(
            id=tenant_id,
            nome_fantasia="Escola Secundária Central",
            nif="123456789",
            status="ATIVO"
        )
        db.add(nova_escola)
        
        # 2. Criar o Utilizador Gestor / Admin
        admin_email = "admin@escola.pt"
        admin_pass = "!1qaz2wsX" # Senha para testarmos
        
        novo_admin = Usuario(
            tenant_id=tenant_id,
            nome_completo="Diretor Silva",
            email=admin_email,
            senha_hash=gerar_hash_senha(admin_pass),
            perfil_acesso="GESTOR"
        )
        db.add(novo_admin)
        
        # Guardar na BD
        await db.commit()
        
        print("\n=== Seed Concluído com Sucesso! ===")
        print(f"Escola Criada: {nova_escola.nome_fantasia}")
        print(f"Email Login: {admin_email}")
        print(f"Password: {admin_pass}")
        print("===================================")

if __name__ == "__main__":
    asyncio.run(carregar_dados_iniciais())