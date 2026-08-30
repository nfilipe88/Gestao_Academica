import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as TransferenciasActions from './transferencias.actions';
import { SolicitacaoTransferencia } from './transferencias.models';
import { PaginaResultado } from '../../shared/models/paginacao.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class TransferenciasEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  criarSolicitacao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(TransferenciasActions.criarSolicitacao),
      switchMap(action => this.http.post<SolicitacaoTransferencia>('/api/v1/transferencias', {
        aluno_id: action.aluno_id, nif_destino: action.nif_destino, motivo: action.motivo ?? null,
      }).pipe(
        switchMap(() => [
          TransferenciasActions.carregarMinhasSolicitacoes({}),
          TransferenciasActions.transferenciasOperacaoSucesso({ mensagem: 'Pedido de transferência enviado à instituição de destino.' })
        ]),
        catchError(err => of(TransferenciasActions.transferenciasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o pedido de transferência.'
        })))
      ))
    )
  );

  carregarMinhasSolicitacoes$ = createEffect(() =>
    this.actions$.pipe(
      ofType(TransferenciasActions.carregarMinhasSolicitacoes),
      switchMap(action => {
        const params: Record<string, string | number> = { page: action.page ?? 1, page_size: action.page_size ?? 25 };
        if (action.status) params['status'] = action.status;
        if (action.data_inicio) params['data_inicio'] = action.data_inicio;
        if (action.data_fim) params['data_fim'] = action.data_fim;
        return this.http.get<PaginaResultado<SolicitacaoTransferencia>>('/api/v1/transferencias/minhas', { params }).pipe(
          map(resp => TransferenciasActions.carregarEnviadasSucesso({
            solicitacoes: resp.items,
            paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
          })),
          catchError(err => of(TransferenciasActions.transferenciasOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar os pedidos de transferência.'
          })))
        );
      })
    )
  );

  carregarSolicitacoesRecebidas$ = createEffect(() =>
    this.actions$.pipe(
      ofType(TransferenciasActions.carregarSolicitacoesRecebidas),
      switchMap(action => this.http.get<PaginaResultado<SolicitacaoTransferencia>>('/api/v1/transferencias/recebidas', {
        params: { page: action.page ?? 1, page_size: action.page_size ?? 25 }
      }).pipe(
        map(resp => TransferenciasActions.carregarRecebidasSucesso({
          solicitacoes: resp.items,
          paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
        })),
        catchError(err => of(TransferenciasActions.transferenciasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os pedidos recebidos.'
        })))
      ))
    )
  );

  carregarSolicitacoesAuditoria$ = createEffect(() =>
    this.actions$.pipe(
      ofType(TransferenciasActions.carregarSolicitacoesAuditoria),
      switchMap(action => this.http.get<PaginaResultado<SolicitacaoTransferencia>>('/api/v1/transferencias', {
        params: { page: action.page ?? 1, page_size: action.page_size ?? 25 }
      }).pipe(
        map(resp => TransferenciasActions.carregarAuditoriaSucesso({
          solicitacoes: resp.items,
          paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
        })),
        catchError(err => of(TransferenciasActions.transferenciasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os pedidos de transferência.'
        })))
      ))
    )
  );

  aprovarSolicitacao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(TransferenciasActions.aprovarSolicitacao),
      switchMap(action => this.http.patch<SolicitacaoTransferencia>(
        `/api/v1/transferencias/${action.solicitacao_id}/aprovar`, {}
      ).pipe(
        switchMap(() => [
          TransferenciasActions.carregarSolicitacoesRecebidas({}),
          TransferenciasActions.transferenciasOperacaoSucesso({ mensagem: 'Transferência aceite e concluída.' })
        ]),
        catchError(err => of(TransferenciasActions.transferenciasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível aceitar a transferência.'
        })))
      ))
    )
  );

  rejeitarSolicitacao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(TransferenciasActions.rejeitarSolicitacao),
      switchMap(action => this.http.patch<SolicitacaoTransferencia>(
        `/api/v1/transferencias/${action.solicitacao_id}/rejeitar`, { observacoes: action.observacoes }
      ).pipe(
        switchMap(() => [
          TransferenciasActions.carregarSolicitacoesRecebidas({}),
          TransferenciasActions.transferenciasOperacaoSucesso({ mensagem: 'Pedido de transferência negado.' })
        ]),
        catchError(err => of(TransferenciasActions.transferenciasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível negar o pedido.'
        })))
      ))
    )
  );
}
