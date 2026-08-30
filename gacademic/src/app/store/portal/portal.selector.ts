import { createFeatureSelector, createSelector } from '@ngrx/store';
import { PortalState } from './portal.reducer';

export const selectPortalState = createFeatureSelector<PortalState>('portal');

export const selectMeusEducandos = createSelector(selectPortalState, (state) => state.educandos);
export const selectHorarioDoEducando = createSelector(selectPortalState, (state) => state.horario);
export const selectBoletimDoEducando = createSelector(selectPortalState, (state) => state.boletim);
export const selectFinanceiroDoEducando = createSelector(selectPortalState, (state) => state.financeiro);
export const selectTarefasDoEducando = createSelector(selectPortalState, (state) => state.tarefas);
export const selectMateriaisDoEducando = createSelector(selectPortalState, (state) => state.materiais);
export const selectMaterialAberto = createSelector(selectPortalState, (state) => state.materialAberto);
export const selectConversaProfVirtual = createSelector(selectPortalState, (state) => state.conversaProfVirtual);
export const selectAProcessarPerguntaProfVirtual = createSelector(selectPortalState, (state) => state.aProcessarPerguntaProfVirtual);
export const selectErroProfVirtual = createSelector(selectPortalState, (state) => state.erroProfVirtual);
export const selectPortalError = createSelector(selectPortalState, (state) => state.erro);
export const selectExamesDoEducando = createSelector(selectPortalState, (state) => state.exames);
export const selectTentativaAtual = createSelector(selectPortalState, (state) => state.tentativaAtual);
export const selectResultadoExame = createSelector(selectPortalState, (state) => state.resultadoExame);
export const selectASubmeterTentativa = createSelector(selectPortalState, (state) => state.aSubmeterTentativa);
export const selectEventosSuspeitosTentativa = createSelector(selectPortalState, (state) => state.eventosSuspeitosTentativa);
export const selectEstatisticasDoEducando = createSelector(selectPortalState, (state) => state.estatisticas);
export const selectComunicadosDoEducando = createSelector(selectPortalState, (state) => state.comunicados);
