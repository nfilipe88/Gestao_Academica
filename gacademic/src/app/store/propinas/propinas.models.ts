// Alinhado com app/schemas/propinas.py — uma linha por Curso/Série,
// com ou sem valor definido ainda para o ano letivo pedido.
export interface LinhaPropina {
  curso_id: string;
  curso_nome: string;
  serie_ano_id: string;
  serie_ano_nome: string;
  propina_id: string | null;
  ano_letivo: number;
  valor_mensalidade: number | null;
  valor_matricula: number | null;
}
