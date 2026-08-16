import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as ConfiguracoesActions from './configuracoes.actions';
import { ConfiguracaoTenant, TipoAvaliacao } from './configuracoes.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class ConfiguracoesEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarConfiguracao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ConfiguracoesActions.carregarConfiguracao),
      switchMap(() => this.http.get<ConfiguracaoTenant>('/api/v1/configuracoes').pipe(
        map(configuracao => ConfiguracoesActions.carregarConfiguracaoSucesso({ configuracao })),
        catchError(err => of(ConfiguracoesActions.configuracoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as configurações da escola.'
        })))
      ))
    )
  );

  atualizarConfiguracao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ConfiguracoesActions.atualizarConfiguracao),
      switchMap(action => this.http.put<ConfiguracaoTenant>('/api/v1/configuracoes', action.dados).pipe(
        switchMap(configuracao => [
          ConfiguracoesActions.carregarConfiguracaoSucesso({ configuracao }),
          ConfiguracoesActions.configuracoesOperacaoSucesso({ mensagem: 'Configurações guardadas com sucesso.' })
        ]),
        catchError(err => of(ConfiguracoesActions.configuracoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível guardar as configurações.'
        })))
      ))
    )
  );

  // ==========================================
  // TIPOS DE AVALIAÇÃO
  // ==========================================
  carregarTiposAvaliacao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ConfiguracoesActions.carregarTiposAvaliacao),
      switchMap(() => this.http.get<TipoAvaliacao[]>('/api/v1/configuracoes/tipos-avaliacao').pipe(
        map(tipos => ConfiguracoesActions.carregarTiposAvaliacaoSucesso({ tipos })),
        catchError(err => of(ConfiguracoesActions.configuracoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os tipos de avaliação.'
        })))
      ))
    )
  );

  criarTipoAvaliacao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ConfiguracoesActions.criarTipoAvaliacao),
      switchMap(action => this.http.post<TipoAvaliacao>('/api/v1/configuracoes/tipos-avaliacao', {
        nome: action.nome, requer_agendamento: action.requer_agendamento
      }).pipe(
        switchMap(() => [
          ConfiguracoesActions.carregarTiposAvaliacao(),
          ConfiguracoesActions.configuracoesOperacaoSucesso({ mensagem: 'Tipo de avaliação criado com sucesso.' })
        ]),
        catchError(err => of(ConfiguracoesActions.configuracoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o tipo de avaliação.'
        })))
      ))
    )
  );

  atualizarTipoAvaliacao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ConfiguracoesActions.atualizarTipoAvaliacao),
      switchMap(action => this.http.put<TipoAvaliacao>(`/api/v1/configuracoes/tipos-avaliacao/${action.id}`, {
        nome: action.nome, requer_agendamento: action.requer_agendamento, ativo: action.ativo
      }).pipe(
        switchMap(() => [
          ConfiguracoesActions.carregarTiposAvaliacao(),
          ConfiguracoesActions.configuracoesOperacaoSucesso({ mensagem: 'Tipo de avaliação atualizado com sucesso.' })
        ]),
        catchError(err => of(ConfiguracoesActions.configuracoesOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar o tipo de avaliação.'
        })))
      ))
    )
  );
}
