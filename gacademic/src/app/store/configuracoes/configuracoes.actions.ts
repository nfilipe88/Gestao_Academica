import { createAction, props } from '@ngrx/store';
import { ConfiguracaoTenant } from './configuracoes.models';

export const carregarConfiguracao = createAction('[Configuracoes] Carregar Configuracao');
export const carregarConfiguracaoSucesso = createAction(
  '[Configuracoes] Carregar Configuracao Sucesso',
  props<{ configuracao: ConfiguracaoTenant }>()
);

export const atualizarConfiguracao = createAction(
  '[Configuracoes] Atualizar Configuracao',
  props<{ dados: ConfiguracaoTenant }>()
);

export const configuracoesOperacaoSucesso = createAction('[Configuracoes] Operacao Sucesso', props<{ mensagem: string }>());
export const configuracoesOperacaoFalhou = createAction('[Configuracoes API] Operação Falhou', props<{ erro: string }>());
