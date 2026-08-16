import { createReducer, on } from '@ngrx/store';
import * as LmsActions from './lms.actions';
import { MaterialAula } from './lms.models';

export interface LmsState {
  materiais: MaterialAula[];
  mensagem: string | null;
  erro: string | null;
  aSugerirConteudo: boolean;
  sugestaoConteudo: string | null;
}

export const initialState: LmsState = {
  materiais: [],
  mensagem: null,
  erro: null,
  aSugerirConteudo: false,
  sugestaoConteudo: null
};

export const lmsReducer = createReducer(
  initialState,
  on(LmsActions.carregarMateriais, LmsActions.criarMaterial, LmsActions.atualizarMaterial, LmsActions.apagarMaterial,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(LmsActions.carregarMateriaisSucesso, (state, { materiais }) => ({ ...state, materiais })),
  on(LmsActions.sugerirConteudo, (state) => ({ ...state, erro: null, aSugerirConteudo: true })),
  on(LmsActions.sugerirConteudoSucesso, (state, { sugestao }) => ({ ...state, aSugerirConteudo: false, sugestaoConteudo: sugestao })),
  on(LmsActions.limparSugestaoConteudo, (state) => ({ ...state, sugestaoConteudo: null })),
  on(LmsActions.lmsOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(LmsActions.lmsOperacaoFalhou, (state, { erro }) => ({ ...state, erro, aSugerirConteudo: false }))
);
