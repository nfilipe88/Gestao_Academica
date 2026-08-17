import { createFeatureSelector, createSelector } from '@ngrx/store';
import { PerfilState } from './perfil.reducer';

export const selectPerfilState = createFeatureSelector<PerfilState>('perfil');
export const selectPerfil = createSelector(selectPerfilState, (state) => state.perfil);
export const selectPerfilMensagem = createSelector(selectPerfilState, (state) => state.mensagem);
export const selectPerfilErro = createSelector(selectPerfilState, (state) => state.erro);
