from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import obter_sessao_db
from app.database.models import Usuario
from typing import List

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuários"])

@router.get("/", response_model=List[dict])
async def listar_usuarios_da_escola(db: AsyncSession = Depends(obter_sessao_db)):
    """
    Retorna apenas os utilizadores pertencentes à escola do token enviado.
    O isolamento é garantido nativamente no PostgreSQL via RLS.
    """
    resultado = await db.execute(select(Usuario))
    usuarios = resultado.scalars().all()
    return [{"id": u.id, "nome": u.nome_completo, "email": u.email} for u in usuarios]