// Alinhado com app/api/v1/portal.py.
import { FaturaMensalidade } from '../financeiro/financeiro.models';

export interface EducandoResumo {
  aluno_id: string;
  nome_completo: string;
  matricula_interna: string;
  matricula_id: string | null;
  status_matricula: string | null;
  ano_letivo: number | null;
  nome_turma: string | null;
}

// A grade horária reaproveita exatamente o formato de HorarioAula do
// módulo Horários (ver store/horarios/horarios.models.ts) — o Portal só
// lê, nunca cria/edita, por isso não precisa de repetir o tipo aqui.
export interface HorarioAulaPortal {
  id: string;
  dia_semana: number;
  hora_inicio: string;
  hora_fim: string;
  sala: string | null;
  nome_turma: string;
  nome_disciplina: string;
  nome_professor: string;
}

export interface NotaBoletim {
  periodo_avaliacao: string;
  tipo_avaliacao: string | null;
  data_avaliacao: string | null;
  valor_nota: number;
}

export interface DisciplinaBoletim {
  disciplina_id: string;
  nome_disciplina: string;
  notas: NotaBoletim[];
  total_aulas: number;
  total_faltas: number;
}

export interface Boletim {
  disciplinas: DisciplinaBoletim[];
}

// Formato reduzido — o extrato de faturas em si reaproveita
// FaturaMensalidade de store/financeiro/financeiro.models.ts.
export interface FinanceiroEducando {
  matricula_id: string | null;
  contrato: {
    id: string;
    valor_total_anual: number;
    quantidade_parcelas: number;
  } | null;
  faturas: FaturaMensalidade[];
}

// Alinhado com cruds/tarefas.py::listar_tarefas_do_aluno.
export interface TarefaEducando {
  tarefa_id: string;
  titulo: string;
  descricao: string | null;
  data_entrega: string;
  valor_maximo: number;
  nome_turma: string;
  nome_disciplina: string;
  status: 'PENDENTE' | 'ENTREGUE' | 'ENTREGUE_ATRASADO' | 'NAO_ENTREGUE';
  nota: number | null;
  observacoes: string | null;
}
