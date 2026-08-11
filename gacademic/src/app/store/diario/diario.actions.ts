import { createAction, props } from '@ngrx/store';
import { AlunoDiario, ConsolidadoTurmaDisciplina, FrequenciaAlunoInput, NotaAlunoInput } from './diario.models';

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
