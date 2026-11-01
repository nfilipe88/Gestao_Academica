"""Schemas Pydantic do Mapa de Permissões (ver models_permissoes.py)."""
import uuid

from pydantic import BaseModel, Field


class PermissaoModuloOut(BaseModel):
    id: uuid.UUID
    ordem: int
    modulo: str
    perfil: str
    pode_criar: bool
    pode_ler: bool
    pode_atualizar: bool
    pode_apagar: bool
    # Teto do código: o que as rotas deste módulo deixam este perfil fazer —
    # o mapa só restringe, nunca dá acima disto (ver core/mapa_permissoes.py).
    codigo_pode_criar: bool = True
    codigo_pode_ler: bool = True
    codigo_pode_atualizar: bool = True
    codigo_pode_apagar: bool = True
    # Linha sem rotas associadas (ex.: Visão Geral) — só descreve, não decide nada.
    informativo: bool = False
    # Operações que nunca se podem tirar (ex.: ler as Configurações).
    protegidas: list[str] = []
    # O que este módulo precisa de LER noutros para o ecrã funcionar — só para avisar.
    leituras_necessarias: list[str] = []
    # Só na vista do Gestor: o que vale na escola dele (mapa base E restrições da escola).
    escola_pode_criar: bool | None = None
    escola_pode_ler: bool | None = None
    escola_pode_atualizar: bool | None = None
    escola_pode_apagar: bool | None = None

    class Config:
        from_attributes = True


class PermissaoModuloUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    pode_criar: bool
    pode_ler: bool
    pode_atualizar: bool
    pode_apagar: bool


class PerfilNomeOut(BaseModel):
    codigo: str
    nome: str
    model_config = {"from_attributes": True}


class PerfilNomeUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    nome: str = Field(..., min_length=2, max_length=60)


# ==========================================
# PERFIS DA ESCOLA (bloco D2 — ver cruds/perfis_personalizados.py)
# ==========================================
class PermissaoPerfilEscolaOut(BaseModel):
    modulo: str
    ordem: int
    informativo: bool
    pode_criar: bool
    pode_ler: bool
    pode_atualizar: bool
    pode_apagar: bool
    # O que o perfil base pode na escola — o teto deste perfil.
    limite_pode_criar: bool
    limite_pode_ler: bool
    limite_pode_atualizar: bool
    limite_pode_apagar: bool
    protegidas: list[str] = []
    leituras_necessarias: list[str] = []


class PerfilPersonalizadoOut(BaseModel):
    id: uuid.UUID
    nome: str
    perfil_base: str
    n_utilizadores: int
    permissoes: list[PermissaoPerfilEscolaOut]


class PerfilPersonalizadoCreate(BaseModel):
    model_config = {"extra": "forbid"}
    nome: str = Field(..., min_length=2, max_length=60)
    perfil_base: str  # SECRETARIA | PROFESSOR


class PerfilPersonalizadoRenomear(BaseModel):
    model_config = {"extra": "forbid"}
    nome: str = Field(..., min_length=2, max_length=60)


class PermissaoPerfilEscolaUpdate(PermissaoModuloUpdate):
    modulo: str = Field(..., max_length=80)


class MinhasPermissoesOut(BaseModel):
    # None = o mapa não restringe esta pessoa (equipa da plataforma).
    modulos: dict[str, dict[str, bool]] | None
    perfil_personalizado: str | None = None
    # {módulo: [o que ele precisa de ler e esta pessoa não pode]} — para o ecrã explicar porquê fica vazio.
    leituras_em_falta: dict[str, list[str]] = {}
