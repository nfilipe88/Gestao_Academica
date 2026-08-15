import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as TransferenciasActions from './transferencias.actions';
import { SolicitacaoTransferencia } from './transferencias.models';
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
          TransferenciasActions.carregarMinhasSolicitacoes(),
          TransferenciasActions.transferenciasOperacaoSucesso({ mensagem: 'Pedido de transferência enviado ao Super Admin.' })
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
      switchMap(() => this.http.get<SolicitacaoTransferencia[]>('/api/v1/transferencias/minhas').pipe(
        map(solicitacoes => TransferenciasActions.carregarSolicitacoesSucesso({ solicitacoes })),
        catchError(err => of(TransferenciasActions.transferenciasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os pedidos de transferência.'
        })))
      ))
    )
  );

  carregarSolicitacoesSuperAdmin$ = createEffect(() =>
    this.actions$.pipe(
      ofType(TransferenciasActions.carregarSolicitacoesSuperAdmin),
      switchMap(() => this.http.get<SolicitacaoTransferencia[]>('/api/v1/transferencias').pipe(
        map(solicitacoes => TransferenciasActions.carregarSolicitacoesSucesso({ solicitacoes })),
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
          TransferenciasActions.carregarSolicitacoesSuperAdmin(),
          TransferenciasActions.transferenciasOperacaoSucesso({ mensagem: 'Transferência aprovada e concluída.' })
        ]),
        catchError(err => of(TransferenciasActions.transferenciasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível aprovar a transferência.'
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
          TransferenciasActions.carregarSolicitacoesSuperAdmin(),
          TransferenciasActions.transferenciasOperacaoSucesso({ mensagem: 'Pedido de transferência rejeitado.' })
        ]),
        catchError(err => of(TransferenciasActions.transferenciasOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível rejeitar o pedido.'
        })))
      ))
    )
  );
}
