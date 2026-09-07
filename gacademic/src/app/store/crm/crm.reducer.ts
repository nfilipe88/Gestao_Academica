import { createReducer, on } from '@ngrx/store';
import * as CrmActions from './crm.actions';
import { FunilEtapa, MensagemLead, OportunidadeCRM } from './crm.models';

export interface CrmState {
  etapas: FunilEtapa[];
  oportunidades: OportunidadeCRM[];
  mensagensPorLead: Record<string, MensagemLead[]>;
  mensagem: string | null;
  erro: string | null;
}

export const initialState: CrmState = {
  etapas: [],
  oportunidades: [],
  mensagensPorLead: {},
  mensagem: null,
  erro: null
};

export const crmReducer = createReducer(
  initialState,
  on(CrmActions.carregarFunil, CrmActions.carregarOportunidades, CrmActions.criarLead,
     CrmActions.atualizarLead, CrmActions.moverOportunidade, CrmActions.atualizarOportunidade,
     CrmActions.carregarMensagensLead, CrmActions.responderLead,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(CrmActions.carregarFunilSucesso, (state, { etapas }) => ({ ...state, etapas })),
  on(CrmActions.carregarOportunidadesSucesso, (state, { oportunidades }) => ({ ...state, oportunidades })),
  on(CrmActions.carregarMensagensLeadSucesso, (state, { lead_id, mensagens }) => ({
    ...state, mensagensPorLead: { ...state.mensagensPorLead, [lead_id]: mensagens }
  })),
  on(CrmActions.crmOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(CrmActions.crmOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
