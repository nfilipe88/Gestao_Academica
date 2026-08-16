import { createAction, props } from '@ngrx/store';
import { ConfiguracaoTenant, TipoAvaliacao } from './configuracoes.models';

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

// ==========================================
// TIPOS DE AVALIAÇÃO (catálogo por escola)
// ==========================================
export const carregarTiposAvaliacao = createAction('[Configuracoes] Carregar Tipos Avaliacao');
export const carregarTiposAvaliacaoSucesso = createAction(
  '[Configuracoes] Carregar Tipos Avaliacao Sucesso',
  props<{ tipos: TipoAvaliacao[] }>()
);

export const criarTipoAvaliacao = createAction(
  '[Configuracoes] Criar Tipo Avaliacao',
  props<{ nome: string; requer_agendamento: boolean }>()
);

export const atualizarTipoAvaliacao = createAction(
  '[Configuracoes] Atualizar Tipo Avaliacao',
  props<{ id: string; nome: string; requer_agendamento: boolean; ativo: boolean }>()
);
