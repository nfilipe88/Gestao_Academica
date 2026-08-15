import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as ConfiguracoesActions from './configuracoes.actions';
import { ConfiguracaoTenant } from './configuracoes.models';
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
}
