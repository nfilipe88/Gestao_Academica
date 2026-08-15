import { createAction, props } from '@ngrx/store';
import {
  CobrancaDocumentoGerada, PrecoDocumento, SolicitacaoDocumentoEmissao, SolicitacaoDocumentoEscola, TemplateDocumento
} from './documentos.models';
import { EstadoPaginacao } from '../../shared/models/paginacao.models';

// --- Preços (Gestor) ---
export const carregarPrecos = createAction('[Documentos] Carregar Precos');
export const carregarPrecosSucesso = createAction('[Documentos] Carregar Precos Sucesso', props<{ precos: PrecoDocumento[] }>());

export const atualizarPreco = createAction(
  '[Documentos] Atualizar Preco',
  props<{ tipo_documento: string, preco: number, ativo: boolean }>()
);

// --- Layouts personalizados por escola (Gestor) ---
export const carregarTemplates = createAction('[Documentos] Carregar Templates');
export const carregarTemplatesSucesso = createAction('[Documentos] Carregar Templates Sucesso', props<{ templates: TemplateDocumento[] }>());

export const guardarTemplate = createAction(
  '[Documentos] Guardar Template',
  props<{ tipo_documento: string, corpo_html: string }>()
);
export const reporTemplatePadrao = createAction('[Documentos] Repor Template Padrao', props<{ tipo_documento: string }>());
// Sucesso de guardar/repor: atualiza só a entrada desse tipo na lista.
export const templateAtualizado = createAction('[Documentos] Template Atualizado', props<{ template: TemplateDocumento }>());

// Pré-visualização não guarda nada — o PDF é tratado no componente
// (mesmo padrão de onVerPdf: pede via HttpClient, abre num separador
// já aberto no clique). Ação só para reportar erro de validação do
// Jinja2 sem passar pelo fluxo genérico de "guardar falhou".
export const templatePreVisualizacaoFalhou = createAction('[Documentos] Template Pre-visualizacao Falhou', props<{ erro: string }>());

// --- Pedidos de emissão (Aluno/Responsável -> Escola) ---
export const criarSolicitacaoEmissao = createAction(
  '[Documentos] Criar Solicitacao Emissao',
  props<{ tipo_documento: string, formato_entrega: string, descricao_outro?: string, aluno_id?: string }>()
);

export const carregarMinhasSolicitacoesEmissao = createAction('[Documentos] Carregar Minhas Solicitacoes Emissao');
export const carregarSolicitacoesEmissaoStaff = createAction(
  '[Documentos] Carregar Solicitacoes Emissao Staff',
  props<{ page?: number, page_size?: number }>()
);
// `paginacao` só vem preenchida quando a origem é a listagem staff
// (paginada no back-end) — a variante "minhas" (Aluno/Responsável)
// devolve sempre a lista completa, sem envelope de paginação.
export const carregarSolicitacoesEmissaoSucesso = createAction(
  '[Documentos] Carregar Solicitacoes Emissao Sucesso',
  props<{ solicitacoes: SolicitacaoDocumentoEmissao[], paginacao?: EstadoPaginacao }>()
);

export const gerarCobrancaDocumento = createAction('[Documentos] Gerar Cobranca Documento', props<{ solicitacao_id: string }>());
export const cobrancaDocumentoGerada = createAction('[Documentos] Cobranca Documento Gerada', props<{ cobranca: CobrancaDocumentoGerada }>());

export const capturarPagamentoDocumento = createAction('[Documentos] Capturar Pagamento Documento', props<{ order_id: string }>());

export const entregarFisico = createAction('[Documentos] Entregar Fisico', props<{ solicitacao_id: string, observacoes?: string }>());
export const cancelarSolicitacaoEmissao = createAction('[Documentos] Cancelar Solicitacao Emissao', props<{ solicitacao_id: string }>());

// --- Pedidos da escola (Escola -> Aluno/Responsável/Professor) ---
export const criarSolicitacaoEscola = createAction(
  '[Documentos] Criar Solicitacao Escola',
  props<{ destinatario_tipo: string, destinatario_id: string, titulo: string, descricao: string }>()
);
export const carregarSolicitacoesEscolaStaff = createAction(
  '[Documentos] Carregar Solicitacoes Escola Staff',
  props<{ page?: number, page_size?: number }>()
);
export const carregarSolicitacoesEscolaStaffSucesso = createAction(
  '[Documentos] Carregar Solicitacoes Escola Staff Sucesso',
  props<{ solicitacoes: SolicitacaoDocumentoEscola[], paginacao: EstadoPaginacao }>()
);

// Pedidos da escola dirigidos ao próprio login (ALUNO/RESPONSAVEL/PROFESSOR)
// — estado separado do acima porque um Professor também é "staff" e as
// duas listagens podiam sobrepor-se se partilhassem a mesma fatia.
export const carregarMinhasSolicitacoesEscola = createAction('[Documentos] Carregar Minhas Solicitacoes Escola');
export const carregarMinhasSolicitacoesEscolaSucesso = createAction(
  '[Documentos] Carregar Minhas Solicitacoes Escola Sucesso',
  props<{ solicitacoes: SolicitacaoDocumentoEscola[] }>()
);

export const responderSolicitacaoEscola = createAction(
  '[Documentos] Responder Solicitacao Escola',
  props<{ solicitacao_id: string, resposta_texto: string }>()
);
export const concluirSolicitacaoEscola = createAction('[Documentos] Concluir Solicitacao Escola', props<{ solicitacao_id: string }>());

export const documentosOperacaoSucesso = createAction('[Documentos] Operacao Sucesso', props<{ mensagem: string }>());

// Ação genérica de falha (mesmo padrão dos restantes módulos).
export const documentosOperacaoFalhou = createAction('[Documentos API] Operação Falhou', props<{ erro: string }>());
