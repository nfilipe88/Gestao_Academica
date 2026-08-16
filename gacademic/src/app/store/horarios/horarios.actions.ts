import { createAction, props } from '@ngrx/store';
import { AulaPorLancar, HorarioAula, HorarioAulaInput } from './horarios.models';

// Gestor/Secretaria: grade completa de uma turma.
export const carregarGradeDaTurma = createAction(
  '[Horarios] Carregar Grade Da Turma',
  props<{ turma_id: string }>()
);
export const carregarGradeDaTurmaSucesso = createAction(
  '[Horarios] Carregar Grade Da Turma Sucesso',
  props<{ horarios: HorarioAula[] }>()
);

// Professor autenticado: a sua própria grade.
export const carregarMinhaGrade = createAction('[Horarios] Carregar Minha Grade');
export const carregarMinhaGradeSucesso = createAction(
  '[Horarios] Carregar Minha Grade Sucesso',
  props<{ horarios: HorarioAula[] }>()
);

// Gestor/Secretaria: grade de um professor específico — usada para
// mostrar, em tempo real no formulário, os horários que esse professor
// já tem ocupados antes de a Secretária tentar gravar (ver
// horarios.component.ts::onAlocacaoOuDiaChange).
export const carregarGradeDoProfessor = createAction(
  '[Horarios] Carregar Grade Do Professor',
  props<{ professor_id: string }>()
);
export const carregarGradeDoProfessorSucesso = createAction(
  '[Horarios] Carregar Grade Do Professor Sucesso',
  props<{ horarios: HorarioAula[] }>()
);
export const limparGradeDoProfessor = createAction('[Horarios] Limpar Grade Do Professor');

// Cruzamento Horário × Diário — aulas que já deviam ter tido chamada
// lançada (segundo o Horário) e ainda não têm registo no Diário.
export const carregarAulasPorLancar = createAction('[Horarios] Carregar Aulas Por Lancar');
export const carregarAulasPorLancarSucesso = createAction(
  '[Horarios] Carregar Aulas Por Lancar Sucesso',
  props<{ aulas: AulaPorLancar[] }>()
);

export const criarHorario = createAction(
  '[Horarios] Criar Horario',
  props<{ dados: HorarioAulaInput, turma_id: string }>()
);

export const atualizarHorario = createAction(
  '[Horarios] Atualizar Horario',
  props<{ horario_id: string, dados: Partial<HorarioAulaInput>, turma_id: string }>()
);

export const removerHorario = createAction(
  '[Horarios] Remover Horario',
  props<{ horario_id: string, turma_id: string }>()
);

export const horariosOperacaoSucesso = createAction(
  '[Horarios] Operacao Sucesso',
  props<{ mensagem: string }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const horariosOperacaoFalhou = createAction(
  '[Horarios API] Operação Falhou',
  props<{ erro: string }>()
);
