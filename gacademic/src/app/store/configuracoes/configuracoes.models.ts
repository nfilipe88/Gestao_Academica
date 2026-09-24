// Alinhado com app/schemas/configuracoes.py.

export interface ConfiguracaoTenant {
  iban: string | null;
  moeda: string;
  // Só diz SE há logótipo — o ficheiro em si sai por GET
  // /configuracoes/logotipo (download autenticado com Authorization,
  // por isso nunca é um <img src> direto — ver configuracoes.component.ts).
  tem_logotipo: boolean;
  telefone_contacto: string | null;
  email_contacto: string | null;
  morada: string | null;
  cidade: string | null;
  codigo_postal: string | null;
  pais: string | null;
  nota_minima_aprovacao: number | null;
  // Critérios do fecho do ano (ver back_end/app/core/resultados.py). Opcionais
  // no tipo: clientes/estados antigos sem estes campos continuam válidos.
  max_disciplinas_reprovadas?: number;
  limite_faltas_percentagem?: number | null;
  // Nota máxima da escala de notas da escola (ex.: 10 ou 20) — sempre
  // presente (campo obrigatório, ver ConfiguracaoTenantUpdate no
  // back-end). Usada por Diário de Classe para validar/limitar o
  // lançamento de notas.
  nota_maxima: number;
  // Valor padrão da taxa de matrícula (encargo único, distinto das
  // mensalidades) — null = a escola não cobra. Usada ao assinar um
  // contrato em Financeiro e pela conversão automática RN01 a partir da
  // candidatura self-service (ver features/public/matricula).
  valor_taxa_matricula: number | null;
  // Ano Letivo corrente — regra geral, início num ano e fim no seguinte
  // (ex.: setembro de 2026 a junho de 2027). data_*_ano_letivo são
  // datas "YYYY-MM-DD" (formato devolvido pelo back-end);
  // ano_letivo_atual é a junção "YYYY/YYYY" dos dois anos (ex.:
  // "2026/2027") — pedido explícito do utilizador, distinto de
  // propósito do inteiro solto usado por Turma.ano_letivo/Matricula.ano_letivo
  // — preenchido automaticamente a partir das duas datas mas continua
  // editável (ver configuracoes.component.ts). Ainda nulo = a escola
  // não completou a configuração inicial (ver
  // core/guards/configuracao-inicial.guard.ts).
  data_inicio_ano_letivo: string | null;
  data_fim_ano_letivo: string | null;
  ano_letivo_atual: string | null;
  // Períodos letivos — hora "HH:MM:SS" (formato devolvido pelo back-end)
  // ou null se ainda não definida. Só guarda a informação por agora;
  // não valida conflitos em Horários.
  periodo_manha_inicio: string | null;
  periodo_manha_fim: string | null;
  periodo_tarde_inicio: string | null;
  periodo_tarde_fim: string | null;
  periodo_pos_laboral_inicio: string | null;
  periodo_pos_laboral_fim: string | null;
  // Aceitação da Política de Privacidade/Termos. null = por aceitar
  // (escola criada pelo Super Admin) — ver core/guards/termos.guard.ts.
  // Opcionais: só se leem, nunca vão no corpo do PUT.
  termos_aceites_em?: string | null;
  termos_versao?: string | null;
  // Inscrições de autoatendimento (candidatura pública e pedido de rematrícula no Portal).
  matriculas_abertas?: boolean;
  rematriculas_abertas?: boolean;
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
// MOEDAS_PAYPAL_SUPORTADAS em app/schemas/configuracoes.py (tem de
// corresponder exatamente). Usada só para decidir quando esconder o
// botão "Pagar com PayPal" a favor do pagamento manual/transferência
// (ver financeiro.component) — nunca para restringir o <select> de
// moeda da escola em si, essa é MOEDAS_SUPORTADAS, abaixo.
export const MOEDAS_PAYPAL_SUPORTADAS = [
  'AUD', 'BRL', 'CAD', 'CHF', 'CNY', 'CZK', 'DKK', 'EUR', 'GBP', 'HKD',
  'HUF', 'ILS', 'JPY', 'MXN', 'MYR', 'NOK', 'NZD', 'PHP', 'PLN', 'SEK',
  'SGD', 'THB', 'TWD', 'USD',
];

// Moedas que a escola pode escolher para os seus próprios preços — ver
// MOEDAS_SUPORTADAS em app/schemas/configuracoes.py (tem de
// corresponder exatamente, para o <select> nunca oferecer uma opção
// que o back-end depois rejeita). Inclui AOA (Kwanza) mesmo não sendo
// aceite pelo PayPal — uma escola em Angola cobra em AOA na mesma,
// só usa o pagamento manual em vez do botão PayPal.
export const MOEDAS_SUPORTADAS = [...MOEDAS_PAYPAL_SUPORTADAS, 'AOA'];

export const CONFIGURACAO_INICIAL: ConfiguracaoTenant = {
  iban: null,
  moeda: 'EUR',
  tem_logotipo: false,
  telefone_contacto: null,
  email_contacto: null,
  morada: null,
  cidade: null,
  codigo_postal: null,
  pais: null,
  nota_minima_aprovacao: null,
  nota_maxima: 10,
  valor_taxa_matricula: null,
  data_inicio_ano_letivo: null,
  data_fim_ano_letivo: null,
  ano_letivo_atual: null,
  periodo_manha_inicio: null,
  periodo_manha_fim: null,
  periodo_tarde_inicio: null,
  periodo_tarde_fim: null,
  periodo_pos_laboral_inicio: null,
  periodo_pos_laboral_fim: null,
};
