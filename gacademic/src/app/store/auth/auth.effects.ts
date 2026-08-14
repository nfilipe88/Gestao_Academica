import { Injectable, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';
import { Actions, createEffect, ofType, ROOT_EFFECTS_INIT } from '@ngrx/effects';
import { HttpClient, HttpParams } from '@angular/common/http';
import * as AuthActions from './auth.actions';
import { UsuarioLogado } from './auth.actions';
import { catchError, map, switchMap, tap, of } from 'rxjs';

@Injectable()
export class AuthEffects {
  // Injeção via campo (inject()), não via construtor: os createEffect()
  // abaixo são campos de classe e, numa classe sem "extends", os campos
  // são inicializados ANTES do corpo do construtor correr. Com injeção
  // por construtor, "this.actions$" ainda estaria undefined nesse
  // momento (TypeError: Cannot read properties of undefined (reading
  // 'pipe')). Usando inject() como campo, a ordem de inicialização (na
  // ordem de declaração) garante que já está pronto quando os efeitos
  // abaixo o usam.
  private actions$ = inject(Actions);
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);
  private router = inject(Router);

  // Ao arrancar a app (só no browser), repõe a sessão gravada no
  // localStorage no estado do NgRx. Sem isto, um F5 faz o store voltar a
  // "deslogado" mesmo com o token ainda válido no localStorage.
  restoreAuth$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ROOT_EFFECTS_INIT),
      map(() => {
        if (!isPlatformBrowser(this.platformId)) {
          return AuthActions.restoreAuth({ token: null, usuario: null });
        }
        const token = localStorage.getItem('saas_access_token');
        const usuarioBruto = localStorage.getItem('saas_user');
        let usuario: UsuarioLogado | null = null;
        try {
          usuario = usuarioBruto ? JSON.parse(usuarioBruto) : null;
        } catch {
          usuario = null;
        }
        return AuthActions.restoreAuth({ token, usuario });
      })
    )
  );

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

  // Sem isto, o login tinha sucesso (token gravado, store atualizada)
  // mas o ecrã ficava parado em /login: nada disparava a navegação.
  // Se o login veio de um redirecionamento (ver auth.guard.ts), volta
  // ao destino original em vez de ir sempre para /dashboard. ALUNO/
  // RESPONSAVEL não têm acesso a /dashboard (é montado com dados de
  // módulos internos vedados a estes perfis — ver exigir_perfil_staff
  // no back-end) — vão antes para /portal. SUPER_ADMIN, pelo mesmo
  // motivo, vai para /admin.
  redirecionarAposLogin$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuthActions.loginSuccess),
      tap(({ usuario }) => {
        const returnUrl = this.router.parseUrl(this.router.url).queryParams['returnUrl'];
        let destinoPorOmissao = '/dashboard';
        if (['ALUNO', 'RESPONSAVEL'].includes(usuario.perfil_acesso)) {
          destinoPorOmissao = '/portal';
        } else if (usuario.perfil_acesso === 'SUPER_ADMIN') {
          destinoPorOmissao = '/admin';
        }
        this.router.navigateByUrl(returnUrl || destinoPorOmissao);
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

  redirecionarAposLogout$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AuthActions.logout),
      tap(() => this.router.navigateByUrl('/login'))
    ),
    { dispatch: false }
  );
}