import { createAction, props } from '@ngrx/store';
import { Boletim, EducandoResumo, FinanceiroEducando, HorarioAulaPortal, TarefaEducando } from './portal.models';

export const carregarMeusEducandos = createAction('[Portal] Carregar Meus Educandos');
export const carregarMeusEducandosSucesso = createAction(
  '[Portal] Carregar Meus Educandos Sucesso',
  props<{ educandos: EducandoResumo[] }>()
);

export const carregarHorarioDoEducando = createAction(
  '[Portal] Carregar Horario Do Educando',
  props<{ aluno_id: string }>()
);
export const carregarHorarioDoEducandoSucesso = createAction(
  '[Portal] Carregar Horario Do Educando Sucesso',
  props<{ horario: HorarioAulaPortal[] }>()
);

export const carregarBoletimDoEducando = createAction(
  '[Portal] Carregar Boletim Do Educando',
  props<{ aluno_id: string }>()
);
export const carregarBoletimDoEducandoSucesso = createAction(
  '[Portal] Carregar Boletim Do Educando Sucesso',
  props<{ boletim: Boletim }>()
);

export const carregarFinanceiroDoEducando = createAction(
  '[Portal] Carregar Financeiro Do Educando',
  props<{ aluno_id: string }>()
);
export const carregarFinanceiroDoEducandoSucesso = createAction(
  '[Portal] Carregar Financeiro Do Educando Sucesso',
  props<{ financeiro: FinanceiroEducando }>()
);

export const carregarTarefasDoEducando = createAction(
  '[Portal] Carregar Tarefas Do Educando',
  props<{ aluno_id: string }>()
);
export const carregarTarefasDoEducandoSucesso = createAction(
  '[Portal] Carregar Tarefas Do Educando Sucesso',
  props<{ tarefas: TarefaEducando[] }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const portalOperacaoFalhou = createAction(
  '[Portal API] Operação Falhou',
  props<{ erro: string }>()
);
