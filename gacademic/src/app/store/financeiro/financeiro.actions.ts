import { createAction, props } from '@ngrx/store';
import { CobrancaGerada, ContratoFinanceiro, Despesa, FaturaMensalidade, MatriculaResumo, ResponsavelElegivel } from './financeiro.models';

export const carregarMatriculasDoAluno = createAction(
  '[Financeiro] Carregar Matriculas Do Aluno',
  props<{ aluno_id: string }>()
);
export const carregarMatriculasDoAlunoSucesso = createAction(
  '[Financeiro] Carregar Matriculas Do Aluno Sucesso',
  props<{ matriculas: MatriculaResumo[] }>()
);

export const carregarResponsaveisDaMatricula = createAction(
  '[Financeiro] Carregar Responsaveis Da Matricula',
  props<{ matricula_id: string }>()
);
export const carregarResponsaveisDaMatriculaSucesso = createAction(
  '[Financeiro] Carregar Responsaveis Da Matricula Sucesso',
  props<{ responsaveis: ResponsavelElegivel[] }>()
);

// Vai ao contrato da matrícula selecionada; se ainda não existir, o
// effect despacha `contratoInexistente` em vez de erro genérico, para o
// componente saber que deve mostrar o formulário "Novo Contrato".
export const carregarContratoDaMatricula = createAction(
  '[Financeiro] Carregar Contrato Da Matricula',
  props<{ matricula_id: string }>()
);
export const carregarContratoDaMatriculaSucesso = createAction(
  '[Financeiro] Carregar Contrato Da Matricula Sucesso',
  props<{ contrato: ContratoFinanceiro }>()
);
export const contratoInexistente = createAction('[Financeiro] Contrato Inexistente');

export const criarContrato = createAction(
  '[Financeiro] Criar Contrato',
  props<{
    matricula_id: string, responsavel_id: string, valor_total_anual: number,
    quantidade_parcelas: number, dia_vencimento_padrao: number, percentual_desconto_bolsa: number,
    valor_taxa_matricula: number | null
  }>()
);

export const carregarFaturasDoContrato = createAction(
  '[Financeiro] Carregar Faturas Do Contrato',
  props<{ contrato_id: string }>()
);
export const carregarFaturasDoContratoSucesso = createAction(
  '[Financeiro] Carregar Faturas Do Contrato Sucesso',
  props<{ faturas: FaturaMensalidade[] }>()
);

export const marcarFaturaPaga = createAction(
  '[Financeiro] Marcar Fatura Paga',
  props<{ fatura_id: string, contrato_id: string, valor_pago: number | null, forma_pagamento: string }>()
);

// Pede ao PayPal os dados de pagamento (approve_url) — o effect abre-a
// numa nova aba assim que a resposta chega.
export const gerarCobranca = createAction(
  '[Financeiro] Gerar Cobranca',
  props<{ fatura_id: string, contrato_id: string, metodo_pagamento: string }>()
);
export const cobrancaGerada = createAction(
  '[Financeiro] Cobranca Gerada',
  props<{ cobranca: CobrancaGerada }>()
);

// Chamado quando o PayPal redireciona de volta com sucesso
// (?paypal_retorno=sucesso&token=<order_id>) — efetiva o pagamento.
export const capturarPagamento = createAction(
  '[Financeiro] Capturar Pagamento',
  props<{ order_id: string, contrato_id: string }>()
);

export const processarReguaCobranca = createAction('[Financeiro] Processar Regua Cobranca');
export const processarReguaCobrancaSucesso = createAction(
  '[Financeiro] Processar Regua Cobranca Sucesso',
  props<{ mensagem: string }>()
);

export const financeiroOperacaoSucesso = createAction(
  '[Financeiro] Operacao Sucesso',
  props<{ mensagem: string }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const financeiroOperacaoFalhou = createAction(
  '[Financeiro API] Operação Falhou',
  props<{ erro: string }>()
);

// --- Despesas (saídas financeiras — ver Estatísticas) ---
export const criarDespesa = createAction(
  '[Financeiro] Criar Despesa',
  props<{ categoria: string, descricao: string, valor: number, data_despesa: string, forma_pagamento?: string }>()
);
export const criarDespesaSucesso = createAction('[Financeiro] Criar Despesa Sucesso', props<{ despesa: Despesa }>());

export const carregarDespesas = createAction(
  '[Financeiro] Carregar Despesas',
  props<{ data_inicio?: string, data_fim?: string, categoria?: string }>()
);
export const carregarDespesasSucesso = createAction('[Financeiro] Carregar Despesas Sucesso', props<{ despesas: Despesa[] }>());

export const removerDespesa = createAction('[Financeiro] Remover Despesa', props<{ despesa_id: string }>());
export const removerDespesaSucesso = createAction('[Financeiro] Remover Despesa Sucesso', props<{ despesa_id: string }>());
