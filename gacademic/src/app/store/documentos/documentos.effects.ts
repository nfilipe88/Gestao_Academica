import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as DocumentosActions from './documentos.actions';
import {
  CobrancaDocumentoGerada, PrecoDocumento, SolicitacaoDocumentoEmissao, SolicitacaoDocumentoEscola, TemplateDocumento
} from './documentos.models';
import { PaginaResultado } from '../../shared/models/paginacao.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class DocumentosEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarPrecos$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.carregarPrecos),
      switchMap(() => this.http.get<PrecoDocumento[]>('/api/v1/documentos/precos').pipe(
        map(precos => DocumentosActions.carregarPrecosSucesso({ precos })),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar a tabela de preços.'
        })))
      ))
    )
  );

  carregarPrecosDisponiveis$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.carregarPrecosDisponiveis),
      switchMap(() => this.http.get<PrecoDocumento[]>('/api/v1/documentos/precos/disponiveis').pipe(
        map(precos => DocumentosActions.carregarPrecosDisponiveisSucesso({ precos })),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os documentos disponíveis para pedido.'
        })))
      ))
    )
  );

  atualizarPreco$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.atualizarPreco),
      switchMap(action => this.http.put<PrecoDocumento>(
        `/api/v1/documentos/precos/${action.tipo_documento}`, { preco: action.preco, ativo: action.ativo }
      ).pipe(
        switchMap(() => [
          DocumentosActions.carregarPrecos(),
          DocumentosActions.documentosOperacaoSucesso({ mensagem: 'Preço atualizado com sucesso.' })
        ]),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar o preço.'
        })))
      ))
    )
  );

  carregarTemplates$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.carregarTemplates),
      switchMap(() => this.http.get<TemplateDocumento[]>('/api/v1/documentos/templates').pipe(
        map(templates => DocumentosActions.carregarTemplatesSucesso({ templates })),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os modelos de documentos.'
        })))
      ))
    )
  );

  guardarTemplate$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.guardarTemplate),
      switchMap(action => this.http.put<TemplateDocumento>(
        `/api/v1/documentos/templates/${action.tipo_documento}`, { corpo_html: action.corpo_html }
      ).pipe(
        switchMap(template => [
          DocumentosActions.templateAtualizado({ template }),
          DocumentosActions.documentosOperacaoSucesso({ mensagem: 'Modelo guardado com sucesso.' })
        ]),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível guardar o modelo.'
        })))
      ))
    )
  );

  reporTemplatePadrao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.reporTemplatePadrao),
      switchMap(action => this.http.delete<TemplateDocumento>(
        `/api/v1/documentos/templates/${action.tipo_documento}`
      ).pipe(
        switchMap(template => [
          DocumentosActions.templateAtualizado({ template }),
          DocumentosActions.documentosOperacaoSucesso({ mensagem: 'Modelo padrão da plataforma reposto.' })
        ]),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível repor o modelo padrão.'
        })))
      ))
    )
  );

  criarSolicitacaoEmissao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.criarSolicitacaoEmissao),
      switchMap(action => this.http.post<SolicitacaoDocumentoEmissao>('/api/v1/documentos/solicitacoes', {
        tipo_documento: action.tipo_documento, formato_entrega: action.formato_entrega,
        descricao_outro: action.descricao_outro ?? null, aluno_id: action.aluno_id ?? null,
      }).pipe(
        switchMap(() => [
          DocumentosActions.carregarMinhasSolicitacoesEmissao(),
          DocumentosActions.documentosOperacaoSucesso({ mensagem: 'Pedido de documento criado. Prossiga com o pagamento para o libertar.' })
        ]),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o pedido de documento.'
        })))
      ))
    )
  );

  carregarMinhasSolicitacoesEmissao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.carregarMinhasSolicitacoesEmissao),
      switchMap(() => this.http.get<SolicitacaoDocumentoEmissao[]>('/api/v1/documentos/solicitacoes/minhas').pipe(
        map(solicitacoes => DocumentosActions.carregarSolicitacoesEmissaoSucesso({ solicitacoes })),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os seus pedidos de documentos.'
        })))
      ))
    )
  );

  carregarSolicitacoesEmissaoStaff$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.carregarSolicitacoesEmissaoStaff),
      switchMap(action => {
        const params: Record<string, string | number> = { page: action.page ?? 1, page_size: action.page_size ?? 25 };
        if (action.status) params['status'] = action.status;
        if (action.data_inicio) params['data_inicio'] = action.data_inicio;
        if (action.data_fim) params['data_fim'] = action.data_fim;
        return this.http.get<PaginaResultado<SolicitacaoDocumentoEmissao>>('/api/v1/documentos/solicitacoes', { params }).pipe(
          map(resp => DocumentosActions.carregarSolicitacoesEmissaoSucesso({
            solicitacoes: resp.items,
            paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
          })),
          catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar os pedidos de documentos.'
          })))
        );
      })
    )
  );

  gerarCobrancaDocumento$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.gerarCobrancaDocumento),
      switchMap(action => this.http.post<CobrancaDocumentoGerada>(
        `/api/v1/documentos/solicitacoes/${action.solicitacao_id}/gerar-cobranca`, {}
      ).pipe(
        // A abertura do separador do PayPal acontece no componente (ver
        // portal.component.ts onPagarComPayPal) — mesmo motivo do módulo
        // Financeiro: por essa altura o gesto de clique original já não
        // está "ativo" para o browser não bloquear window.open() como pop-up.
        map(cobranca => DocumentosActions.cobrancaDocumentoGerada({ cobranca })),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível gerar a cobrança junto do PayPal.'
        })))
      ))
    )
  );

  capturarPagamentoDocumento$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.capturarPagamentoDocumento),
      switchMap(action => this.http.post<SolicitacaoDocumentoEmissao>(
        `/api/v1/documentos/solicitacoes/capturar?order_id=${encodeURIComponent(action.order_id)}`, {}
      ).pipe(
        switchMap(() => [
          DocumentosActions.carregarMinhasSolicitacoesEmissao(),
          DocumentosActions.documentosOperacaoSucesso({ mensagem: 'Pagamento confirmado.' })
        ]),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível confirmar o pagamento junto do PayPal.'
        })))
      ))
    )
  );

  entregarFisico$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.entregarFisico),
      switchMap(action => this.http.patch<SolicitacaoDocumentoEmissao>(
        `/api/v1/documentos/solicitacoes/${action.solicitacao_id}/entregar-fisico`, { observacoes: action.observacoes ?? null }
      ).pipe(
        switchMap(() => [
          DocumentosActions.carregarSolicitacoesEmissaoStaff({}),
          DocumentosActions.documentosOperacaoSucesso({ mensagem: 'Entrega registada.' })
        ]),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível registar a entrega.'
        })))
      ))
    )
  );

  cancelarSolicitacaoEmissao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.cancelarSolicitacaoEmissao),
      switchMap(action => this.http.patch<SolicitacaoDocumentoEmissao>(
        `/api/v1/documentos/solicitacoes/${action.solicitacao_id}/cancelar`, {}
      ).pipe(
        switchMap(() => [
          DocumentosActions.carregarSolicitacoesEmissaoStaff({}),
          DocumentosActions.documentosOperacaoSucesso({ mensagem: 'Pedido cancelado.' })
        ]),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível cancelar o pedido.'
        })))
      ))
    )
  );

  criarSolicitacaoEscola$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.criarSolicitacaoEscola),
      switchMap(action => this.http.post<SolicitacaoDocumentoEscola>('/api/v1/documentos/pedidos-escola', {
        destinatario_tipo: action.destinatario_tipo, destinatario_id: action.destinatario_id,
        titulo: action.titulo, descricao: action.descricao,
      }).pipe(
        switchMap(() => [
          DocumentosActions.carregarSolicitacoesEscolaStaff({}),
          DocumentosActions.documentosOperacaoSucesso({ mensagem: 'Pedido enviado.' })
        ]),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível enviar o pedido.'
        })))
      ))
    )
  );

  carregarSolicitacoesEscolaStaff$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.carregarSolicitacoesEscolaStaff),
      switchMap(action => {
        const params: Record<string, string | number> = { page: action.page ?? 1, page_size: action.page_size ?? 25 };
        if (action.status) params['status'] = action.status;
        if (action.data_inicio) params['data_inicio'] = action.data_inicio;
        if (action.data_fim) params['data_fim'] = action.data_fim;
        return this.http.get<PaginaResultado<SolicitacaoDocumentoEscola>>('/api/v1/documentos/pedidos-escola', { params }).pipe(
          map(resp => DocumentosActions.carregarSolicitacoesEscolaStaffSucesso({
            solicitacoes: resp.items,
            paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
          })),
          catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar os pedidos feitos aos alunos/professores.'
          })))
        );
      })
    )
  );

  carregarMinhasSolicitacoesEscola$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.carregarMinhasSolicitacoesEscola),
      switchMap(() => this.http.get<SolicitacaoDocumentoEscola[]>('/api/v1/documentos/pedidos-escola/minhas').pipe(
        map(solicitacoes => DocumentosActions.carregarMinhasSolicitacoesEscolaSucesso({ solicitacoes })),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os pedidos que a escola lhe fez.'
        })))
      ))
    )
  );

  responderSolicitacaoEscola$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.responderSolicitacaoEscola),
      switchMap(action => this.http.patch<SolicitacaoDocumentoEscola>(
        `/api/v1/documentos/pedidos-escola/${action.solicitacao_id}/responder`, { resposta_texto: action.resposta_texto }
      ).pipe(
        switchMap(() => [
          DocumentosActions.carregarMinhasSolicitacoesEscola(),
          DocumentosActions.documentosOperacaoSucesso({ mensagem: 'Resposta enviada.' })
        ]),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível enviar a resposta.'
        })))
      ))
    )
  );

  concluirSolicitacaoEscola$ = createEffect(() =>
    this.actions$.pipe(
      ofType(DocumentosActions.concluirSolicitacaoEscola),
      switchMap(action => this.http.patch<SolicitacaoDocumentoEscola>(
        `/api/v1/documentos/pedidos-escola/${action.solicitacao_id}/concluir`, {}
      ).pipe(
        switchMap(() => [
          DocumentosActions.carregarSolicitacoesEscolaStaff({}),
          DocumentosActions.documentosOperacaoSucesso({ mensagem: 'Pedido concluído.' })
        ]),
        catchError(err => of(DocumentosActions.documentosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível concluir o pedido.'
        })))
      ))
    )
  );
}
