import { createReducer, on } from '@ngrx/store';
import * as PortalActions from './portal.actions';
import {
  Boletim, EducandoResumo, FinanceiroEducando, HorarioAulaPortal,
  MaterialEducando, MaterialEducandoDetalhe, MensagemProfVirtual, TarefaEducando
} from './portal.models';

export interface PortalState {
  educandos: EducandoResumo[];
  horario: HorarioAulaPortal[];
  boletim: Boletim | null;
  financeiro: FinanceiroEducando | null;
  tarefas: TarefaEducando[];
  materiais: MaterialEducando[];
  materialAberto: MaterialEducandoDetalhe | null;
  conversaProfVirtual: MensagemProfVirtual[];
  aProcessarPerguntaProfVirtual: boolean;
  erroProfVirtual: string | null;
  erro: string | null;
}

export const initialState: PortalState = {
  educandos: [],
  horario: [],
  boletim: null,
  financeiro: null,
  tarefas: [],
  materiais: [],
  materialAberto: null,
  conversaProfVirtual: [],
  aProcessarPerguntaProfVirtual: false,
  erroProfVirtual: null,
  erro: null
};

export const portalReducer = createReducer(
  initialState,
  on(PortalActions.carregarMeusEducandos, PortalActions.carregarHorarioDoEducando,
     PortalActions.carregarBoletimDoEducando, PortalActions.carregarFinanceiroDoEducando,
     PortalActions.carregarTarefasDoEducando, PortalActions.carregarMateriaisDoEducando,
     PortalActions.carregarMaterialDoEducando,
    (state) => ({ ...state, erro: null })
  ),
  on(PortalActions.carregarMeusEducandosSucesso, (state, { educandos }) => ({ ...state, educandos })),
  on(PortalActions.carregarHorarioDoEducandoSucesso, (state, { horario }) => ({ ...state, horario })),
  on(PortalActions.carregarBoletimDoEducandoSucesso, (state, { boletim }) => ({ ...state, boletim })),
  on(PortalActions.carregarFinanceiroDoEducandoSucesso, (state, { financeiro }) => ({ ...state, financeiro })),
  on(PortalActions.carregarTarefasDoEducandoSucesso, (state, { tarefas }) => ({ ...state, tarefas })),
  on(PortalActions.carregarMateriaisDoEducandoSucesso, (state, { materiais }) => ({ ...state, materiais })),
  on(PortalActions.carregarMaterialDoEducandoSucesso, (state, { material }) => ({ ...state, materialAberto: material })),
  on(PortalActions.limparMaterialAberto, (state) => ({
    ...state, materialAberto: null, conversaProfVirtual: [], erroProfVirtual: null
  })),
  on(PortalActions.perguntarProfVirtual, (state, { pergunta }) => ({
    ...state,
    conversaProfVirtual: [...state.conversaProfVirtual, { papel: 'aluno' as const, texto: pergunta }],
    aProcessarPerguntaProfVirtual: true,
    erroProfVirtual: null
  })),
  on(PortalActions.perguntarProfVirtualSucesso, (state, { resposta }) => ({
    ...state,
    conversaProfVirtual: [...state.conversaProfVirtual, { papel: 'assistente' as const, texto: resposta }],
    aProcessarPerguntaProfVirtual: false
  })),
  on(PortalActions.perguntarProfVirtualFalhou, (state, { erro }) => ({
    ...state, aProcessarPerguntaProfVirtual: false, erroProfVirtual: erro
  })),
  on(PortalActions.portalOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
