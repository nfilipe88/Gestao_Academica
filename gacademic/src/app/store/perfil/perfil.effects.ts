import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as PerfilActions from './perfil.actions';
import { Perfil } from './perfil.models';
import { catchError, map, of, switchMap, tap } from 'rxjs';
import { tokenRenovado } from '../auth/auth.actions';

@Injectable()
export class PerfilEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarPerfil$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PerfilActions.carregarPerfil),
      switchMap(() => this.http.get<Perfil>('/api/v1/perfil').pipe(
        map(perfil => PerfilActions.carregarPerfilSucesso({ perfil })),
        catchError(err => of(PerfilActions.perfilOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o seu perfil.'
        })))
      ))
    )
  );

  atualizarPerfil$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PerfilActions.atualizarPerfil),
      switchMap(action => this.http.put<Perfil>('/api/v1/perfil', {
        nome_completo: action.nome_completo, email: action.email,
        ...(action.senha_atual ? { senha_atual: action.senha_atual } : {})
      }).pipe(
        switchMap(perfil => [
          PerfilActions.carregarPerfilSucesso({ perfil }),
          PerfilActions.perfilOperacaoSucesso({ mensagem: 'Dados atualizados com sucesso.' })
        ]),
        catchError(err => of(PerfilActions.perfilOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar os seus dados.'
        })))
      ))
    )
  );

  alterarSenha$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PerfilActions.alterarSenha),
      switchMap(action => this.http.post<{ mensagem: string; access_token: string }>('/api/v1/perfil/alterar-senha', {
        senha_atual: action.senha_atual, nova_senha: action.nova_senha
      }).pipe(
        // Mudar a palavra-passe termina todas as sessões, incluindo esta —
        // continua com o token novo devolvido (o refresh token novo já
        // veio no cookie HttpOnly).
        tap(res => localStorage.setItem('saas_access_token', res.access_token)),
        switchMap(res => [
          tokenRenovado({ token: res.access_token }),
          PerfilActions.perfilOperacaoSucesso({ mensagem: res.mensagem })
        ]),
        catchError(err => of(PerfilActions.perfilOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível alterar a palavra-passe.'
        })))
      ))
    )
  );
}
