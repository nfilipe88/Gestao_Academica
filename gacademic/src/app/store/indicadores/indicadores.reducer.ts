import { createReducer, on } from '@ngrx/store';
import * as IndicadoresActions from './indicadores.actions';
import { AlunoRisco, Indicadores, TrilhaRecuperacao } from './indicadores.models';

export interface IndicadoresState {
  indicadores: Indicadores | null;
  alunosEmRisco: AlunoRisco[] | null;
  // Última trilha gerada nesta sessão, por matrícula — não é o
  // histórico completo (esse tem endpoint próprio, GET .../trilhas,
  // por agora só consultado à parte); isto é só para mostrar o
  // resultado logo a seguir a "Gerar".
  trilhasPorMatricula: Record<string, TrilhaRecuperacao>;
  // A geração da trilha é uma chamada real à IA (alguns segundos) —
  // sem isto o Gestor não sabe se o clique em "Gerar" já está a
  // processar, e podia voltar a clicar.
  aGerarTrilhaPorMatricula: Record<string, boolean>;
  erro: string | null;
}

export const initialState: IndicadoresState = {
  indicadores: null,
  alunosEmRisco: null,
  trilhasPorMatricula: {},
  aGerarTrilhaPorMatricula: {},
  erro: null
};

export const indicadoresReducer = createReducer(
  initialState,
  on(IndicadoresActions.carregarIndicadores, IndicadoresActions.carregarRiscoEvasao, (state) => ({ ...state, erro: null })),
  on(IndicadoresActions.carregarIndicadoresSucesso, (state, { indicadores }) => ({ ...state, indicadores })),
  on(IndicadoresActions.carregarRiscoEvasaoSucesso, (state, { alunosEmRisco }) => ({ ...state, alunosEmRisco })),
  on(IndicadoresActions.gerarTrilhaRecuperacao, (state, { matricula_id }) => ({
    ...state, erro: null, aGerarTrilhaPorMatricula: { ...state.aGerarTrilhaPorMatricula, [matricula_id]: true }
  })),
  on(IndicadoresActions.gerarTrilhaRecuperacaoSucesso, (state, { matricula_id, trilha }) => ({
    ...state,
    trilhasPorMatricula: { ...state.trilhasPorMatricula, [matricula_id]: trilha },
    aGerarTrilhaPorMatricula: { ...state.aGerarTrilhaPorMatricula, [matricula_id]: false }
  })),
  // Falha genérica (o erro não identifica a matrícula) — limpa todos os
  // spinners em curso em vez de deixar algum preso indefinidamente.
  on(IndicadoresActions.indicadoresOperacaoFalhou, (state, { erro }) => ({ ...state, erro, aGerarTrilhaPorMatricula: {} }))
);
