import { createReducer, on } from '@ngrx/store';
import * as DiarioActions from './diario.actions';
import {
  AlunoDiario, Avaliacao, AvaliacaoAgendada, ConsolidadoTurmaDisciplina, NotaAvaliacaoInput, NotaExameNacional, NotaFinal,
  PeriodoAvaliacao
} from './diario.models';

export interface DiarioState {
  alunos: AlunoDiario[];
  consolidado: ConsolidadoTurmaDisciplina | null;
  periodos: PeriodoAvaliacao[];
  avaliacoes: Avaliacao[];
  avaliacoesAgendadas: AvaliacaoAgendada[];
  notasAvaliacaoSelecionada: NotaAvaliacaoInput[];
  notasFinais: NotaFinal[];
  notasExameNacional: NotaExameNacional[];
  mensagem: string | null;
  erro: string | null;
}

export const initialState: DiarioState = {
  alunos: [],
  consolidado: null,
  periodos: [],
  avaliacoes: [],
  avaliacoesAgendadas: [],
  notasAvaliacaoSelecionada: [],
  notasFinais: [],
  notasExameNacional: [],
  mensagem: null,
  erro: null
};

export const diarioReducer = createReducer(
  initialState,
  on(DiarioActions.carregarAlunosDiario, DiarioActions.lancarFrequencias,
     DiarioActions.lancarNotas, DiarioActions.carregarConsolidado,
     DiarioActions.carregarPeriodos, DiarioActions.criarPeriodo,
     DiarioActions.trancarPeriodo, DiarioActions.reabrirPeriodo, DiarioActions.atualizarJanelaPeriodo,
     DiarioActions.carregarAvaliacoes, DiarioActions.criarAvaliacao,
     DiarioActions.atualizarAvaliacao, DiarioActions.apagarAvaliacao,
     DiarioActions.carregarNotasAvaliacao, DiarioActions.lancarNotasAvaliacao,
     DiarioActions.carregarNotasFinais, DiarioActions.agendarAvaliacaoGeral,
     DiarioActions.carregarAvaliacoesAgendadas,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(DiarioActions.carregarAlunosDiarioSucesso, (state, { alunos }) => ({ ...state, alunos })),
  on(DiarioActions.carregarConsolidadoSucesso, (state, { consolidado }) => ({ ...state, consolidado })),
  on(DiarioActions.carregarPeriodosSucesso, (state, { periodos }) => ({ ...state, periodos })),
  on(DiarioActions.carregarAvaliacoesSucesso, (state, { avaliacoes }) => ({ ...state, avaliacoes })),
  on(DiarioActions.carregarAvaliacoesAgendadasSucesso, (state, { avaliacoesAgendadas }) => ({ ...state, avaliacoesAgendadas })),
  on(DiarioActions.carregarNotasAvaliacaoSucesso, (state, { notas }) => ({ ...state, notasAvaliacaoSelecionada: notas })),
  on(DiarioActions.carregarNotasFinaisSucesso, (state, { notasFinais }) => ({ ...state, notasFinais })),
  on(DiarioActions.carregarNotasExameNacionalSucesso, (state, { notasExameNacional }) => ({ ...state, notasExameNacional })),
  on(DiarioActions.diarioOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(DiarioActions.diarioOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
