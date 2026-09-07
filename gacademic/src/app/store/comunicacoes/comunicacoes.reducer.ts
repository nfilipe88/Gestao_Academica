import { createReducer, on } from '@ngrx/store';
import * as ComunicacoesActions from './comunicacoes.actions';
import { Comunicado, RespostaComunicado } from './comunicacoes.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

export interface ComunicacoesState {
  comunicados: Comunicado[];
  paginacaoComunicados: EstadoPaginacao;
  respostas: RespostaComunicado[];
  erro: string | null;
}

export const initialState: ComunicacoesState = {
  comunicados: [],
  paginacaoComunicados: PAGINACAO_INICIAL,
  respostas: [],
  erro: null
};

export const comunicacoesReducer = createReducer(
  initialState,
  on(ComunicacoesActions.carregarComunicados, ComunicacoesActions.criarComunicado,
     ComunicacoesActions.carregarRespostasComunicado,
    (state) => ({ ...state, erro: null })
  ),
  on(ComunicacoesActions.carregarComunicadosSucesso, (state, { comunicados, paginacao }) => ({ ...state, comunicados, paginacaoComunicados: paginacao })),
  on(ComunicacoesActions.carregarRespostasComunicadoSucesso, (state, { respostas }) => ({ ...state, respostas })),
  on(ComunicacoesActions.comunicacoesOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
