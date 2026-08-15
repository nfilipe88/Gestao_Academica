import { createReducer, on } from '@ngrx/store';
import * as DocumentosActions from './documentos.actions';
import { CobrancaDocumentoGerada, PrecoDocumento, SolicitacaoDocumentoEmissao, SolicitacaoDocumentoEscola } from './documentos.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

export interface DocumentosState {
  precos: PrecoDocumento[];
  solicitacoesEmissao: SolicitacaoDocumentoEmissao[];
  paginacaoSolicitacoesEmissao: EstadoPaginacao;
  ultimaCobranca: CobrancaDocumentoGerada | null;
  solicitacoesEscolaStaff: SolicitacaoDocumentoEscola[];
  paginacaoSolicitacoesEscolaStaff: EstadoPaginacao;
  minhasSolicitacoesEscola: SolicitacaoDocumentoEscola[];
  mensagem: string | null;
  erro: string | null;
}

export const initialState: DocumentosState = {
  precos: [],
  solicitacoesEmissao: [],
  paginacaoSolicitacoesEmissao: PAGINACAO_INICIAL,
  ultimaCobranca: null,
  solicitacoesEscolaStaff: [],
  paginacaoSolicitacoesEscolaStaff: PAGINACAO_INICIAL,
  minhasSolicitacoesEscola: [],
  mensagem: null,
  erro: null,
};

export const documentosReducer = createReducer(
  initialState,

  on(DocumentosActions.carregarPrecosSucesso, (state, { precos }) => ({ ...state, precos, erro: null })),

  on(DocumentosActions.carregarSolicitacoesEmissaoSucesso, (state, { solicitacoes, paginacao }) => ({
    ...state, solicitacoesEmissao: solicitacoes,
    ...(paginacao ? { paginacaoSolicitacoesEmissao: paginacao } : {}),
    erro: null
  })),
  on(DocumentosActions.cobrancaDocumentoGerada, (state, { cobranca }) => ({ ...state, ultimaCobranca: cobranca })),

  on(DocumentosActions.carregarSolicitacoesEscolaStaffSucesso, (state, { solicitacoes, paginacao }) => ({
    ...state, solicitacoesEscolaStaff: solicitacoes, paginacaoSolicitacoesEscolaStaff: paginacao, erro: null
  })),
  on(DocumentosActions.carregarMinhasSolicitacoesEscolaSucesso, (state, { solicitacoes }) => ({ ...state, minhasSolicitacoesEscola: solicitacoes, erro: null })),

  on(DocumentosActions.documentosOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem, erro: null })),
  on(DocumentosActions.documentosOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
