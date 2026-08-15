// Alinhado com app/core/paginacao.py — envelope devolvido por toda
// listagem que pode crescer sem limite com o tamanho da escola.

export interface PaginaResultado<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface EstadoPaginacao {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const PAGINACAO_INICIAL: EstadoPaginacao = {
  total: 0,
  page: 1,
  page_size: 25,
  total_pages: 0,
};

export const TAMANHOS_PAGINA = [10, 25, 50, 100] as const;
