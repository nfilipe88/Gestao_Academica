// Tipos alinhados com os schemas devolvidos pelo back-end
// (app/database/models_academico.py / app/api/v1/academico.py).

export interface Curso {
  id: string;
  tenant_id: string;
  nome: string;
}

export interface SerieAno {
  id: string;
  tenant_id: string;
  curso_id: string;
  nome: string;
}

export interface Turma {
  id: string;
  tenant_id: string;
  serie_ano_id: string;
  nome_codigo: string;
  ano_letivo: number;
  vagas_maximas: number;
}
