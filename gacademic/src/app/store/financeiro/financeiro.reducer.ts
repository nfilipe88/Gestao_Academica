import { createReducer, on } from '@ngrx/store';
import * as FinanceiroActions from './financeiro.actions';
import { CobrancaGerada, ContratoFinanceiro, Despesa, FaturaMensalidade, MatriculaResumo, ResponsavelElegivel } from './financeiro.models';

export interface FinanceiroState {
  matriculas: MatriculaResumo[];
  responsaveis: ResponsavelElegivel[];
  contrato: ContratoFinanceiro | null;
  contratoCarregado: boolean; // distingue "ainda não pedi" de "pedi e não existe"
  faturas: FaturaMensalidade[];
  ultimaCobranca: CobrancaGerada | null; // consumida pelo componente para navegar o separador do PayPal já aberto
  despesas: Despesa[];
  mensagem: string | null;
  erro: string | null;
}

export const initialState: FinanceiroState = {
  matriculas: [],
  responsaveis: [],
  contrato: null,
  contratoCarregado: false,
  faturas: [],
  ultimaCobranca: null,
  despesas: [],
  mensagem: null,
  erro: null
};

export const financeiroReducer = createReducer(
  initialState,
  on(FinanceiroActions.carregarMatriculasDoAluno, FinanceiroActions.carregarResponsaveisDaMatricula,
     FinanceiroActions.carregarFaturasDoContrato, FinanceiroActions.criarContrato,
     FinanceiroActions.marcarFaturaPaga, FinanceiroActions.processarReguaCobranca,
     FinanceiroActions.capturarPagamento,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(FinanceiroActions.gerarCobranca, (state) => ({ ...state, erro: null, mensagem: null, ultimaCobranca: null })),
  on(FinanceiroActions.cobrancaGerada, (state, { cobranca }) => ({ ...state, ultimaCobranca: cobranca })),
  on(FinanceiroActions.carregarContratoDaMatricula, (state) => ({
    ...state, erro: null, mensagem: null, contrato: null, contratoCarregado: false, faturas: []
  })),
  on(FinanceiroActions.carregarMatriculasDoAlunoSucesso, (state, { matriculas }) => ({ ...state, matriculas })),
  on(FinanceiroActions.carregarResponsaveisDaMatriculaSucesso, (state, { responsaveis }) => ({ ...state, responsaveis })),
  on(FinanceiroActions.carregarContratoDaMatriculaSucesso, (state, { contrato }) => ({
    ...state, contrato, contratoCarregado: true
  })),
  on(FinanceiroActions.contratoInexistente, (state) => ({ ...state, contrato: null, contratoCarregado: true })),
  on(FinanceiroActions.carregarFaturasDoContratoSucesso, (state, { faturas }) => ({ ...state, faturas })),
  on(FinanceiroActions.processarReguaCobrancaSucesso, FinanceiroActions.financeiroOperacaoSucesso,
    (state, { mensagem }) => ({ ...state, mensagem })
  ),
  on(FinanceiroActions.financeiroOperacaoFalhou, (state, { erro }) => ({ ...state, erro })),

  on(FinanceiroActions.carregarDespesasSucesso, (state, { despesas }) => ({ ...state, despesas })),
  on(FinanceiroActions.criarDespesaSucesso, (state, { despesa }) => ({
    ...state, despesas: [despesa, ...state.despesas]
  })),
  on(FinanceiroActions.removerDespesaSucesso, (state, { despesa_id }) => ({
    ...state, despesas: state.despesas.filter(d => d.id !== despesa_id)
  })),
);
