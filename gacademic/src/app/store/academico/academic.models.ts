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

export interface Disciplina {
  id: string;
  tenant_id: string;
  nome: string;
  carga_horaria_total: number | null;
}

export interface GradeCurricular {
  id: string;
  tenant_id: string;
  serie_ano_id: string;
  disciplina_id: string;
}

// Tópico do currículo dentro de uma disciplina (ex.: "Células" em
// Ciências) — ver models_academico.py::ObjetivoAprendizagem. Cada
// Avaliacao do Diário (ver store/diario/diario.models.ts) pode
// apontar para um destes, para o Painel de Indicadores conseguir
// medir a eficiência por tópico, não só por disciplina inteira.
export interface ObjetivoAprendizagem {
  id: string;
  tenant_id: string;
  disciplina_id: string;
  nome: string;
  descricao: string | null;
}
