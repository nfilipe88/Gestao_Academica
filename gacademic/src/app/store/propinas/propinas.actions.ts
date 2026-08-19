import { createAction, props } from '@ngrx/store';
import { LinhaPropina } from './propinas.models';

export const carregarPropinas = createAction(
  '[Propinas] Carregar Propinas',
  props<{ ano_letivo: number }>()
);
export const carregarPropinasSucesso = createAction(
  '[Propinas] Carregar Propinas Sucesso',
  props<{ linhas: LinhaPropina[] }>()
);

// Upsert — sem botão "Guardar" à parte por linha... na verdade tem
// (o valor é digitado antes de confirmar), mas é sempre a mesma ação
// quer a série já tivesse valor quer não.
export const definirPropina = createAction(
  '[Propinas] Definir Propina',
  props<{ serie_ano_id: string; ano_letivo: number; valor_mensalidade: number; valor_matricula: number | null }>()
);
export const definirPropinaSucesso = createAction(
  '[Propinas] Definir Propina Sucesso',
  props<{ linha: LinhaPropina }>()
);

export const apagarPropina = createAction(
  '[Propinas] Apagar Propina',
  props<{ propina_id: string; serie_ano_id: string }>()
);
export const apagarPropinaSucesso = createAction(
  '[Propinas] Apagar Propina Sucesso',
  props<{ serie_ano_id: string }>()
);

export const propinasOperacaoFalhou = createAction(
  '[Propinas API] Operação Falhou',
  props<{ erro: string }>()
);
