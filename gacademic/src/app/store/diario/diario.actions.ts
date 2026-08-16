import { createAction, props } from '@ngrx/store';
import {
  AlunoDiario, Avaliacao, AvaliacaoAgendada, ConsolidadoTurmaDisciplina, FrequenciaAlunoInput,
  NotaAlunoInput, NotaAvaliacaoInput, NotaFinal, PeriodoAvaliacao
} from './diario.models';

export const carregarAlunosDiario = createAction(
  '[Diario] Carregar Alunos',
  props<{ turma_id: string, disciplina_id: string }>()
);
export const carregarAlunosDiarioSucesso = createAction(
  '[Diario] Carregar Alunos Sucesso',
  props<{ alunos: AlunoDiario[] }>()
);

export const lancarFrequencias = createAction(
  '[Diario] Lancar Frequencias',
  props<{
    turma_id: string, disciplina_id: string, data_aula: string,
    quantidade_aulas: number, conteudo_programado: string | null,
    frequencias: FrequenciaAlunoInput[]
  }>()
);

export const lancarNotas = createAction(
  '[Diario] Lancar Notas',
  props<{
    turma_id: string, disciplina_id: string, periodo_avaliacao: string,
    tipo_avaliacao: string | null, data_avaliacao: string | null,
    notas: NotaAlunoInput[]
  }>()
);

export const carregarConsolidado = createAction(
  '[Diario] Carregar Consolidado',
  props<{ turma_id: string, disciplina_id: string, periodo_avaliacao: string | null }>()
);
export const carregarConsolidadoSucesso = createAction(
  '[Diario] Carregar Consolidado Sucesso',
  props<{ consolidado: ConsolidadoTurmaDisciplina }>()
);

// RN03 — Períodos de Avaliação (janela de lançamento)
export const carregarPeriodos = createAction('[Diario] Carregar Periodos');
export const carregarPeriodosSucesso = createAction(
  '[Diario] Carregar Periodos Sucesso',
  props<{ periodos: PeriodoAvaliacao[] }>()
);
export const criarPeriodo = createAction(
  '[Diario] Criar Periodo',
  props<{ nome: string }>()
);
export const trancarPeriodo = createAction(
  '[Diario] Trancar Periodo',
  props<{ periodo_id: string }>()
);
export const reabrirPeriodo = createAction(
  '[Diario] Reabrir Periodo',
  props<{ periodo_id: string }>()
);

// Avaliações (provas e contínuas) + nota final calculada
export const carregarAvaliacoes = createAction(
  '[Diario] Carregar Avaliacoes',
  props<{ turma_id: string, disciplina_id: string, periodo_avaliacao: string }>()
);
export const carregarAvaliacoesSucesso = createAction(
  '[Diario] Carregar Avaliacoes Sucesso',
  props<{ avaliacoes: Avaliacao[] }>()
);

export const criarAvaliacao = createAction(
  '[Diario] Criar Avaliacao',
  props<{
    turma_id: string, disciplina_id: string, periodo_avaliacao: string,
    titulo: string, tipo_avaliacao: string, peso: number, data_avaliacao: string | null,
    hora_inicio: string | null, hora_fim: string | null, sala: string | null, data_limite_correcao: string | null,
    objetivo_aprendizagem_id: string | null
  }>()
);

export const atualizarAvaliacao = createAction(
  '[Diario] Atualizar Avaliacao',
  props<{
    avaliacao_id: string, turma_id: string, disciplina_id: string, periodo_avaliacao: string,
    titulo: string, tipo_avaliacao: string, peso: number, data_avaliacao: string | null,
    hora_inicio: string | null, hora_fim: string | null, sala: string | null, data_limite_correcao: string | null,
    objetivo_aprendizagem_id: string | null
  }>()
);

export const apagarAvaliacao = createAction(
  '[Diario] Apagar Avaliacao',
  props<{ avaliacao_id: string, turma_id: string, disciplina_id: string, periodo_avaliacao: string }>()
);

// Agendamento "Geral" (toda a escola) — ver POST /diario/avaliacoes/agendar-geral.
export const agendarAvaliacaoGeral = createAction(
  '[Diario] Agendar Avaliacao Geral',
  props<{
    periodo_avaliacao: string, titulo: string, tipo_avaliacao: string, peso: number,
    data_avaliacao: string, hora_inicio: string, hora_fim: string, sala: string | null, data_limite_correcao: string | null
  }>()
);

// Avaliações com hora marcada num intervalo — alimenta o painel de Horários.
export const carregarAvaliacoesAgendadas = createAction(
  '[Diario] Carregar Avaliacoes Agendadas',
  props<{ data_inicio: string | null, data_fim: string | null }>()
);
export const carregarAvaliacoesAgendadasSucesso = createAction(
  '[Diario] Carregar Avaliacoes Agendadas Sucesso',
  props<{ avaliacoesAgendadas: AvaliacaoAgendada[] }>()
);

export const carregarNotasAvaliacao = createAction(
  '[Diario] Carregar Notas Avaliacao',
  props<{ avaliacao_id: string }>()
);
export const carregarNotasAvaliacaoSucesso = createAction(
  '[Diario] Carregar Notas Avaliacao Sucesso',
  props<{ notas: NotaAvaliacaoInput[] }>()
);

export const lancarNotasAvaliacao = createAction(
  '[Diario] Lancar Notas Avaliacao',
  props<{ avaliacao_id: string, turma_id: string, disciplina_id: string, periodo_avaliacao: string, notas: NotaAvaliacaoInput[] }>()
);

export const carregarNotasFinais = createAction(
  '[Diario] Carregar Notas Finais',
  props<{ turma_id: string, disciplina_id: string, periodo_avaliacao: string }>()
);
export const carregarNotasFinaisSucesso = createAction(
  '[Diario] Carregar Notas Finais Sucesso',
  props<{ notasFinais: NotaFinal[] }>()
);

export const diarioOperacaoSucesso = createAction(
  '[Diario] Operacao Sucesso',
  props<{ mensagem: string }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const diarioOperacaoFalhou = createAction(
  '[Diario API] Operação Falhou',
  props<{ erro: string }>()
);
