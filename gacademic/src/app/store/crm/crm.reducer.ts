import { createReducer, on } from '@ngrx/store';
import * as CrmActions from './crm.actions';
import { FunilEtapa, OportunidadeCRM } from './crm.models';

export interface CrmState {
  etapas: FunilEtapa[];
  oportunidades: OportunidadeCRM[];
  mensagem: string | null;
  erro: string | null;
}

export const initialState: CrmState = {
  etapas: [],
  oportunidades: [],
  mensagem: null,
  erro: null
};

export const crmReducer = createReducer(
  initialState,
  on(CrmActions.carregarFunil, CrmActions.carregarOportunidades, CrmActions.criarLead,
     CrmActions.atualizarLead, CrmActions.moverOportunidade,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(CrmActions.carregarFunilSucesso, (state, { etapas }) => ({ ...state, etapas })),
  on(CrmActions.carregarOportunidadesSucesso, (state, { oportunidades }) => ({ ...state, oportunidades })),
  on(CrmActions.crmOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(CrmActions.crmOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
