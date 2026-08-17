import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as PerfilActions from './perfil.actions';
import { Perfil } from './perfil.models';
import { catchError, map, of, switchMap } from 'rxjs';

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
        nome_completo: action.nome_completo, email: action.email
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
      switchMap(action => this.http.post<{ mensagem: string }>('/api/v1/perfil/alterar-senha', {
        senha_atual: action.senha_atual, nova_senha: action.nova_senha
      }).pipe(
        map(res => PerfilActions.perfilOperacaoSucesso({ mensagem: res.mensagem })),
        catchError(err => of(PerfilActions.perfilOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível alterar a palavra-passe.'
        })))
      ))
    )
  );
}
