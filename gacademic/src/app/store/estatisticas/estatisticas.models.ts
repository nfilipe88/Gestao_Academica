// Alinhado com app/api/v1/estatisticas.py e app/cruds/estatisticas.py.
// Distinto de Indicadores (store/indicadores): Indicadores é "tudo em
// tempo real, sem filtros"; Estatísticas existe especificamente para
// escolher um período e tirar um documento (.xlsx/.xls).

export interface FaixaEtaria {
  faixa: string; // "5-9" | "10-14" | "15-18" | "19+"
  total: number;
}

export interface CursoConcorrido {
  curso_id: string;
  nome_curso: string;
  total_matriculados: number;
}

export interface DisciplinaAproveitamento {
  disciplina_id: string;
  nome_disciplina: string;
  media: number;
  total_notas: number;
}

export interface TurmaMelhorNota {
  turma_id: string;
  nome_turma: string;
  media: number;
  total_alunos_avaliados: number;
}

export interface AlunoMelhorNota {
  aluno_id: string;
  nome_aluno: string;
  media: number;
  total_notas: number;
}

export interface ResumoFinanceiroAtual {
  faturas_em_aberto: number;
  faturas_atrasadas: number;
  valor_total_atraso: number;
  contratos_ativos: number;
}

export interface DashboardEstatisticas {
  total_alunos_matriculados: number;
  faixas_etarias: FaixaEtaria[];
  cursos_mais_concorridos: CursoConcorrido[];
  disciplinas_maior_aproveitamento: DisciplinaAproveitamento[];
  turmas_melhores_notas: TurmaMelhorNota[];
  alunos_melhores_notas: AlunoMelhorNota[];
  resumo_financeiro: ResumoFinanceiroAtual;
}

export interface PagamentoMes {
  mes: string; // "YYYY-MM"
  total_pagamentos: number;
  valor_total: number;
}

export interface DespesaMes {
  mes: string;
  total_despesas: number;
  valor_total: number;
}

export interface MaiorEntrada {
  fatura_id: string;
  nome_aluno: string;
  valor: number;
  data_pagamento: string;
  forma_pagamento: string;
}

export interface MaiorSaida {
  despesa_id: string;
  categoria: string;
  descricao: string;
  valor: number;
  data_despesa: string;
}

export interface AtrasosPeriodo {
  total_faturas_atrasadas: number;
  valor_total_atraso: number;
}

export interface RelatorioEstatisticas extends DashboardEstatisticas {
  data_inicio: string;
  data_fim: string;
  matriculas_no_periodo: number;
  pagamentos_por_mes: PagamentoMes[];
  atrasos_periodo: AtrasosPeriodo;
  maiores_entradas: MaiorEntrada[];
  despesas_por_mes: DespesaMes[];
  maiores_saidas: MaiorSaida[];
  total_entradas_periodo: number;
  total_saidas_periodo: number;
  saldo_periodo: number;
}
