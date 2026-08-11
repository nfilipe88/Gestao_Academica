// Alinhado com app/api/v1/diario.py.

export interface AlunoDiario {
  matricula_id: string;
  nome_aluno: string;
  matricula_interna: string;
  numero_chamada: number;
}

export interface ConsolidadoTurmaDisciplina {
  total_alunos: number;
  media_turma: number | null;
  alunos_abaixo_da_media: number;
  total_faltas: number;
}

export interface FrequenciaAlunoInput {
  matricula_id: string;
  presenca: boolean;
  faltas: number;
}

export interface NotaAlunoInput {
  matricula_id: string;
  valor_nota: number;
}
