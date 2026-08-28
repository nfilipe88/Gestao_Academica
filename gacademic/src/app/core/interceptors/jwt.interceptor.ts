import { HttpClient, HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Store } from '@ngrx/store';
import { selectToken } from '../../store/auth/auth.selectors';
import { sessaoExpirada } from '../../store/auth/auth.actions';
import { switchMap } from 'rxjs/internal/operators/switchMap';
import { catchError, Observable, of, shareReplay, take, throwError } from 'rxjs';

// Partilhado entre todos os pedidos: se vários pedidos apanharem 401 ao
// mesmo tempo (ex.: várias chamadas em paralelo quando o access token
// acaba de expirar), só o PRIMEIRO dispara o refresh — os outros
// esperam pelo mesmo resultado (shareReplay) em vez de cada um pedir
// (e rodar) o refresh token, o que invalidaria o dos outros a meio
// (ver rotação em cruds/auth.py::renovar_access_token).
let refrescarEmCurso$: Observable<string | null> | null = null;

function refrescarToken(http: HttpClient, platformId: object): Observable<string | null> {
  if (refrescarEmCurso$) return refrescarEmCurso$;

  const refreshToken = isPlatformBrowser(platformId) ? localStorage.getItem('saas_refresh_token') : null;
  if (!refreshToken) return of(null);

  refrescarEmCurso$ = http.post<{ access_token: string; refresh_token: string }>('/api/v1/auth/refresh', { refresh_token: refreshToken }).pipe(
    switchMap(res => {
      if (isPlatformBrowser(platformId)) {
        localStorage.setItem('saas_access_token', res.access_token);
        localStorage.setItem('saas_refresh_token', res.refresh_token);
      }
      return of(res.access_token);
    }),
    catchError(() => of(null)),
    shareReplay(1),
  );
  // Liberta o "lock" assim que este ciclo terminar (sucesso ou falha) —
  // o próximo 401 (já depois deste refresh resolvido) volta a tentar
  // do zero, em vez de ficar preso ao resultado antigo.
  refrescarEmCurso$.subscribe({ complete: () => { refrescarEmCurso$ = null; } });

  return refrescarEmCurso$;
}

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const store = inject(Store);
  const http = inject(HttpClient);
  const platformId = inject(PLATFORM_ID);

  // Nunca tenta refresh nestes — evita recursão (o próprio /refresh a
  // falhar não pode tentar-se refrescar a si próprio) e /login é
  // sempre "password errada", não "sessão a expirar".
  const ehPedidoDeAuth = req.url.includes('/api/v1/auth/login') || req.url.includes('/api/v1/auth/refresh');

  return store.select(selectToken).pipe(
    take(1),
    switchMap(token => {
      if (!token && isPlatformBrowser(platformId)) {
        token = localStorage.getItem('saas_access_token');
      }
      const finalReq = token
        ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
        : req;

      return next(finalReq).pipe(
        catchError((erro: HttpErrorResponse) => {
          if (erro.status !== 401 || ehPedidoDeAuth) {
            return throwError(() => erro);
          }
          // Um 401 aqui pode ser só o access token curto (~20 min) a ter
          // expirado — tenta trocar por um novo antes de desistir da
          // sessão. Só dispara sessaoExpirada (logout forçado) se o
          // refresh também falhar (refresh token igualmente expirado/
          // revogado, ou nunca existiu).
          return refrescarToken(http, platformId).pipe(
            switchMap(novoToken => {
              if (!novoToken) {
                store.dispatch(sessaoExpirada());
                return throwError(() => erro);
              }
              return next(req.clone({ setHeaders: { Authorization: `Bearer ${novoToken}` } }));
            })
          );
        })
      );
    })
  );
};
