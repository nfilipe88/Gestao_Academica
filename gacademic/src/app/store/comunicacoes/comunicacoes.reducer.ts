import { createReducer, on } from '@ngrx/store';
import * as ComunicacoesActions from './comunicacoes.actions';
import { Comunicado } from './comunicacoes.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

export interface ComunicacoesState {
  comunicados: Comunicado[];
  paginacaoComunicados: EstadoPaginacao;
  erro: string | null;
}

export const initialState: ComunicacoesState = {
  comunicados: [],
  paginacaoComunicados: PAGINACAO_INICIAL,
  erro: null
};

export const comunicacoesReducer = createReducer(
  initialState,
  on(ComunicacoesActions.carregarComunicados, ComunicacoesActions.criarComunicado,
    (state) => ({ ...state, erro: null })
  ),
  on(ComunicacoesActions.carregarComunicadosSucesso, (state, { comunicados, paginacao }) => ({ ...state, comunicados, paginacaoComunicados: paginacao })),
  on(ComunicacoesActions.comunicacoesOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
