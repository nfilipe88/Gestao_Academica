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
};
