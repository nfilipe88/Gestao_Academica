// Alinhado com app/api/v1/indicadores.py.

export interface OcupacaoTurma {
  turma_id: string;
  nome_turma: string;
  vagas_maximas: number;
  matriculados: number;
  taxa_ocupacao: number;
}

export interface ResumoAcademico {
  total_alunos_ativos: number;
  total_vagas: number;
  taxa_ocupacao_geral: number;
  ocupacao_por_turma: OcupacaoTurma[];
}

export interface DesempenhoTurma {
  turma_id: string;
  nome_turma: string;
  media: number | null;
  total_alunos_avaliados: number;
}

export interface ResumoFinanceiro {
  total_faturas_em_aberto: number;
  total_faturas_atrasadas: number;
  taxa_inadimplencia: number;
  valor_total_em_atraso: number;
  receita_recebida_mes_atual: number;
  total_contratos_ativos: number;
}

export interface EtapaFunil {
  etapa_id: string;
  nome_etapa: string;
  eh_etapa_ganho: boolean;
  total: number;
}

export interface FunilCrm {
  funil: EtapaFunil[];
  total_leads: number;
  total_convertidos: number;
  taxa_conversao: number;
}

// Eficiência de aprendizagem por tópico do currículo (ex.: "Células"
// em Ciências) — só inclui objetivos com pelo menos uma nota lançada.
// Ver cruds/indicadores.py::obter_eficiencia_por_objetivo.
export interface EficienciaObjetivo {
  disciplina_id: string;
  nome_disciplina: string;
  objetivo_id: string;
  nome_objetivo: string;
  media_objetivo: number;
  media_disciplina: number | null;
  total_notas: number;
  abaixo_da_media: boolean;
}

export interface Indicadores {
  academico: ResumoAcademico;
  desempenho_por_turma: DesempenhoTurma[];
  eficiencia_por_objetivo: EficienciaObjetivo[];
  financeiro: ResumoFinanceiro;
  crm: FunilCrm;
}
