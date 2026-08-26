// Alinhado com app/schemas/configuracoes.py.

export interface ConfiguracaoTenant {
  iban: string | null;
  moeda: string;
  telefone_contacto: string | null;
  email_contacto: string | null;
  morada: string | null;
  cidade: string | null;
  codigo_postal: string | null;
  pais: string | null;
  nota_minima_aprovacao: number | null;
  // Períodos letivos — hora "HH:MM:SS" (formato devolvido pelo back-end)
  // ou null se ainda não definida. Só guarda a informação por agora;
  // não valida conflitos em Horários.
  periodo_manha_inicio: string | null;
  periodo_manha_fim: string | null;
  periodo_tarde_inicio: string | null;
  periodo_tarde_fim: string | null;
  periodo_pos_laboral_inicio: string | null;
  periodo_pos_laboral_fim: string | null;
}

// Catálogo de tipos de avaliação da escola — ver
// app/database/models_diario.py::TipoAvaliacaoConfig. requer_agendamento
// é o que decide o RBAC: tipos marcados assim só podem ser
// criados/editados por Gestor/Secretaria, com data/hora obrigatórias.
export interface TipoAvaliacao {
  id: string;
  nome: string;
  requer_agendamento: boolean;
  ativo: boolean;
}

// Moedas efetivamente aceites pela PayPal Orders API — ver
// MOEDAS_SUPORTADAS em app/schemas/configuracoes.py (tem de
// corresponder exatamente, para o <select> nunca oferecer uma opção
// que o back-end depois rejeita).
export const MOEDAS_SUPORTADAS = [
  'AUD', 'BRL', 'CAD', 'CHF', 'CNY', 'CZK', 'DKK', 'EUR', 'GBP', 'HKD',
  'HUF', 'ILS', 'JPY', 'MXN', 'MYR', 'NOK', 'NZD', 'PHP', 'PLN', 'SEK',
  'SGD', 'THB', 'TWD', 'USD',
];

export const CONFIGURACAO_INICIAL: ConfiguracaoTenant = {
  iban: null,
  moeda: 'EUR',
  telefone_contacto: null,
  email_contacto: null,
  morada: null,
  cidade: null,
  codigo_postal: null,
  pais: null,
  nota_minima_aprovacao: null,
  periodo_manha_inicio: null,
  periodo_manha_fim: null,
  periodo_tarde_inicio: null,
  periodo_tarde_fim: null,
  periodo_pos_laboral_inicio: null,
  periodo_pos_laboral_fim: null,
};
