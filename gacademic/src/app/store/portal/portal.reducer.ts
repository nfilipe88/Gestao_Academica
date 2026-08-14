import { createReducer, on } from '@ngrx/store';
import * as PortalActions from './portal.actions';
import { Boletim, EducandoResumo, FinanceiroEducando, HorarioAulaPortal, TarefaEducando } from './portal.models';

export interface PortalState {
  educandos: EducandoResumo[];
  horario: HorarioAulaPortal[];
  boletim: Boletim | null;
  financeiro: FinanceiroEducando | null;
  tarefas: TarefaEducando[];
  erro: string | null;
}

export const initialState: PortalState = {
  educandos: [],
  horario: [],
  boletim: null,
  financeiro: null,
  tarefas: [],
  erro: null
};

export const portalReducer = createReducer(
  initialState,
  on(PortalActions.carregarMeusEducandos, PortalActions.carregarHorarioDoEducando,
     PortalActions.carregarBoletimDoEducando, PortalActions.carregarFinanceiroDoEducando,
     PortalActions.carregarTarefasDoEducando,
    (state) => ({ ...state, erro: null })
  ),
  on(PortalActions.carregarMeusEducandosSucesso, (state, { educandos }) => ({ ...state, educandos })),
  on(PortalActions.carregarHorarioDoEducandoSucesso, (state, { horario }) => ({ ...state, horario })),
  on(PortalActions.carregarBoletimDoEducandoSucesso, (state, { boletim }) => ({ ...state, boletim })),
  on(PortalActions.carregarFinanceiroDoEducandoSucesso, (state, { financeiro }) => ({ ...state, financeiro })),
  on(PortalActions.carregarTarefasDoEducandoSucesso, (state, { tarefas }) => ({ ...state, tarefas })),
  on(PortalActions.portalOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
