import { createReducer, on } from '@ngrx/store';
import * as DocumentosActions from './documentos.actions';
import { CobrancaDocumentoGerada, PrecoDocumento, SolicitacaoDocumentoEmissao, SolicitacaoDocumentoEscola } from './documentos.models';

export interface DocumentosState {
  precos: PrecoDocumento[];
  solicitacoesEmissao: SolicitacaoDocumentoEmissao[];
  ultimaCobranca: CobrancaDocumentoGerada | null;
  solicitacoesEscolaStaff: SolicitacaoDocumentoEscola[];
  minhasSolicitacoesEscola: SolicitacaoDocumentoEscola[];
  mensagem: string | null;
  erro: string | null;
}

export const initialState: DocumentosState = {
  precos: [],
  solicitacoesEmissao: [],
  ultimaCobranca: null,
  solicitacoesEscolaStaff: [],
  minhasSolicitacoesEscola: [],
  mensagem: null,
  erro: null,
};

export const documentosReducer = createReducer(
  initialState,

  on(DocumentosActions.carregarPrecosSucesso, (state, { precos }) => ({ ...state, precos, erro: null })),

  on(DocumentosActions.carregarSolicitacoesEmissaoSucesso, (state, { solicitacoes }) => ({ ...state, solicitacoesEmissao: solicitacoes, erro: null })),
  on(DocumentosActions.cobrancaDocumentoGerada, (state, { cobranca }) => ({ ...state, ultimaCobranca: cobranca })),

  on(DocumentosActions.carregarSolicitacoesEscolaStaffSucesso, (state, { solicitacoes }) => ({ ...state, solicitacoesEscolaStaff: solicitacoes, erro: null })),
  on(DocumentosActions.carregarMinhasSolicitacoesEscolaSucesso, (state, { solicitacoes }) => ({ ...state, minhasSolicitacoesEscola: solicitacoes, erro: null })),

  on(DocumentosActions.documentosOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem, erro: null })),
  on(DocumentosActions.documentosOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
