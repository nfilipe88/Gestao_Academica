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

export interface PeriodoAvaliacao {
  id: string;
  nome: string;
  aberto: boolean;
  data_fecho: string | null;
}

// O catálogo de tipos deixou de ser fixo — cada escola define os seus
// em Configurações (ver store/configuracoes::TipoAvaliacao/selectTiposAvaliacaoAtivos).
// tipo_avaliacao aqui é só o nome (texto), validado no back-end contra esse catálogo.

// Uma prova ou avaliação contínua concreta dentro de um período — a
// nota final do período (ver NotaFinal) passa a ser a média ponderada
// (por "peso") das avaliações com nota lançada nesse período.
// hora_inicio/hora_fim/sala/data_limite_correcao só se aplicam a tipos
// com requer_agendamento=true (ex.: "Prova") — ver
// app/cruds/diario.py::_validar_agendamento.
export interface Avaliacao {
  id: string;
  turma_id: string;
  disciplina_id: string;
  periodo_avaliacao: string;
  titulo: string;
  tipo_avaliacao: string;
  peso: number;
  data_avaliacao: string | null;
  hora_inicio: string | null;
  hora_fim: string | null;
  sala: string | null;
  data_limite_correcao: string | null;
  grupo_agendamento_id: string | null;
  objetivo_aprendizagem_id: string | null;
  data_criacao: string;
}

// Avaliação com hora marcada, listada para o painel de Horários — ver
// GET /diario/avaliacoes/agendadas.
export interface AvaliacaoAgendada extends Avaliacao {
  turma_nome: string;
  disciplina_nome: string;
}

export interface NotaAvaliacaoInput {
  matricula_id: string;
  valor_nota: number;
}

// Nota final de um aluno num período — calculada a partir das
// avaliações (calculada_automaticamente=true) ou lançada diretamente
// à mão (lançamentos antigos, antes desta funcionalidade existir).
export interface NotaFinal {
  matricula_id: string;
  nome_aluno: string;
  valor_nota: number | null;
  calculada_automaticamente: boolean;
}
