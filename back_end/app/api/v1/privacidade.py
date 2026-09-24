import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import privacidade
from app.core.exportacao_titular import exportar_titular
from app.core.security import exigir_perfil
from app.database.session import obter_sessao_db

router = APIRouter(prefix="/api/v1/privacidade", tags=["Privacidade"])
logger = logging.getLogger("privacidade")

_PODE_EXPORTAR = exigir_perfil("GESTOR")


@router.get("/exportar/{tipo}/{titular_id}")
async def exportar_dados_do_titular(
    tipo: Literal["aluno", "responsavel", "usuario"],
    titular_id: uuid.UUID,
    db: AsyncSession = Depends(obter_sessao_db),
    utilizador: dict = Depends(_PODE_EXPORTAR),
):
    """Exporta, em JSON, todos os dados que a escola tem sobre um titular (aluno,
    responsável ou utilizador/professor), para responder a um pedido de acesso ou
    portabilidade. Só o Gestor: o ficheiro contém dados pessoais completos."""
    dados = await exportar_titular(db, utilizador["tenant_id"], tipo, titular_id)
    if dados is None:
        raise HTTPException(status_code=404, detail="Titular não encontrado nesta escola.")

    logger.info("Exportação de dados: tenant=%s por=%s tipo=%s titular=%s", utilizador["tenant_id"], utilizador.get("usuario_id"), tipo, titular_id)
    corpo = {
        "titular": {"tipo": tipo, "id": str(titular_id)},
        "exportado_em": datetime.now(timezone.utc).isoformat(),
        "politica_versao": privacidade.VERSAO_TERMOS,
        "nota": "Ficheiros anexados aparecem só com nome e tipo; o conteúdo pode ser pedido à escola. Hashes e tokens nunca são exportados.",
        "dados": dados,
    }
    return JSONResponse(corpo, headers={"Content-Disposition": f'attachment; filename="dados-{tipo}-{titular_id}.json"'})
