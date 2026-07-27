import { Injectable, PLATFORM_ID, Inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient, HttpParams } from '@angular/common/http';
import * as AuthActions from './auth.actions';
import { catchError, map, switchMap, tap, of } from 'rxjs';

@Injectable()
export class AuthEffects {
  
  // Refatorado para Injeção via Construtor (100% Seguro no SSR)
  constructor(
    private actions$: Actions,
    private http: HttpClient,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  login$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuthActions.iniciarLogin),
      switchMap(action => {
        const body = new HttpParams()
          .set('username', action.email)
          .set('password', action.palavraPasse);

        return this.http.post<any>('/api/v1/auth/login', body.toString(), {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        }).pipe(
          map(res => AuthActions.loginSuccess({ 
            token: res.access_token, 
            usuario: res.utilizador 
          })),
          catchError(err => of(AuthActions.loginFalhou({ 
            erro: err.error?.detail || 'Erro na autenticação.' 
          })))
        );
      })
    )
  );

  saveAuthData$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuthActions.loginSuccess),
      tap(({ token, usuario }) => {
        if (isPlatformBrowser(this.platformId)) {
          localStorage.setItem('saas_access_token', token);
          localStorage.setItem('saas_user', JSON.stringify(usuario));
        }
      })
    ),
    { dispatch: false } 
  );

  clearAuthData$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuthActions.logout),
      tap(() => {
        if (isPlatformBrowser(this.platformId)) {
          localStorage.removeItem('saas_access_token');
          localStorage.removeItem('saas_user');
        }
      })
    ),
    { dispatch: false }
  );
}