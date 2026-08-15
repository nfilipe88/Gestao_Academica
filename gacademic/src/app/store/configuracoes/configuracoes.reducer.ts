import { createReducer, on } from '@ngrx/store';
import * as ConfiguracoesActions from './configuracoes.actions';
import { CONFIGURACAO_INICIAL, ConfiguracaoTenant } from './configuracoes.models';

export interface ConfiguracoesState {
  configuracao: ConfiguracaoTenant;
  carregada: boolean; // distingue "ainda não chegou do back-end" de "veio tudo null" — evita mostrar moeda EUR por defeito só porque a chamada ainda está em curso
  mensagem: string | null;
  erro: string | null;
}

export const initialState: ConfiguracoesState = {
  configuracao: CONFIGURACAO_INICIAL,
  carregada: false,
  mensagem: null,
  erro: null,
};

export const configuracoesReducer = createReducer(
  initialState,
  on(ConfiguracoesActions.carregarConfiguracaoSucesso, (state, { configuracao }) => ({
    ...state, configuracao, carregada: true, erro: null,
  })),
  on(ConfiguracoesActions.configuracoesOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem, erro: null })),
  on(ConfiguracoesActions.configuracoesOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
