// Alinhado com app/api/v1/horarios.py / app/cruds/horarios.py.

export interface HorarioAula {
  id: string;
  alocacao_id: string;
  dia_semana: number; // 1=Segunda ... 7=Domingo (ISO 8601)
  hora_inicio: string; // "HH:MM:SS"
  hora_fim: string;
  sala: string | null;
  turma_id: string;
  nome_turma: string;
  disciplina_id: string;
  nome_disciplina: string;
  professor_id: string;
  nome_professor: string;
}

export interface HorarioAulaInput {
  alocacao_id: string;
  dia_semana: number;
  hora_inicio: string;
  hora_fim: string;
  sala: string | null;
}
