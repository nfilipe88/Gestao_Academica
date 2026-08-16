import { createAction, props } from '@ngrx/store';
import {
  Boletim, EducandoResumo, FinanceiroEducando, HorarioAulaPortal,
  MaterialEducando, MaterialEducandoDetalhe, MensagemProfVirtual, TarefaEducando
} from './portal.models';

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

// LMS mínimo — materiais de aula do educando
export const carregarMateriaisDoEducando = createAction(
  '[Portal] Carregar Materiais Do Educando',
  props<{ aluno_id: string }>()
);
export const carregarMateriaisDoEducandoSucesso = createAction(
  '[Portal] Carregar Materiais Do Educando Sucesso',
  props<{ materiais: MaterialEducando[] }>()
);

export const carregarMaterialDoEducando = createAction(
  '[Portal] Carregar Material Do Educando',
  props<{ aluno_id: string, material_id: string }>()
);
export const carregarMaterialDoEducandoSucesso = createAction(
  '[Portal] Carregar Material Do Educando Sucesso',
  props<{ material: MaterialEducandoDetalhe }>()
);
// Ao trocar de material (ou sair da página), limpa o material aberto e
// a conversa — sem isto, abrir um material novo mostrava por instantes
// o conteúdo/chat do anterior.
export const limparMaterialAberto = createAction('[Portal] Limpar Material Aberto');

// Prof. Virtual — chat sem persistência (ver store/portal/portal.effects.ts)
export const perguntarProfVirtual = createAction(
  '[Portal] Perguntar Prof Virtual',
  props<{ aluno_id: string, material_id: string, historico: MensagemProfVirtual[], pergunta: string }>()
);
export const perguntarProfVirtualSucesso = createAction(
  '[Portal] Perguntar Prof Virtual Sucesso',
  props<{ resposta: string }>()
);
export const perguntarProfVirtualFalhou = createAction(
  '[Portal] Perguntar Prof Virtual Falhou',
  props<{ erro: string }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const portalOperacaoFalhou = createAction(
  '[Portal API] Operação Falhou',
  props<{ erro: string }>()
);
