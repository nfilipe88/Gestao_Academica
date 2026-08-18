import { createAction, props } from '@ngrx/store';
import { AlunoRisco, Indicadores, TrilhaRecuperacao } from './indicadores.models';

export const carregarIndicadores = createAction('[Indicadores] Carregar Indicadores');
export const carregarIndicadoresSucesso = createAction(
  '[Indicadores] Carregar Indicadores Sucesso',
  props<{ indicadores: Indicadores }>()
);

// Lista detalhada (o agregado acima só traz a contagem por nível, ver
// Indicadores.risco_evasao_resumo) — pedida à parte porque tem o seu
// próprio endpoint, mais pesado de calcular do que o resto do painel.
export const carregarRiscoEvasao = createAction('[Indicadores] Carregar Risco de Evasão');
export const carregarRiscoEvasaoSucesso = createAction(
  '[Indicadores] Carregar Risco de Evasão Sucesso',
  props<{ alunosEmRisco: AlunoRisco[] }>()
);

// Trilha de recuperação (Prof. Virtual/IA) — pedida a um clique, por
// aluno já sinalizado pelo motor de risco (ver risco-evasao acima).
export const gerarTrilhaRecuperacao = createAction(
  '[Indicadores] Gerar Trilha de Recuperação',
  props<{ matricula_id: string }>()
);
export const gerarTrilhaRecuperacaoSucesso = createAction(
  '[Indicadores] Gerar Trilha de Recuperação Sucesso',
  props<{ matricula_id: string, trilha: TrilhaRecuperacao }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const indicadoresOperacaoFalhou = createAction(
  '[Indicadores API] Operação Falhou',
  props<{ erro: string }>()
);
