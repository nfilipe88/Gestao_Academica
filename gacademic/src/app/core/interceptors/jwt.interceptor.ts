import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Store } from '@ngrx/store';
import { selectToken } from '../../store/auth/auth.selectors';
import { sessaoExpirada } from '../../store/auth/auth.actions';
import { switchMap } from 'rxjs/internal/operators/switchMap';
import { catchError, take, throwError } from 'rxjs';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const store = inject(Store);
  const platformId = inject(PLATFORM_ID);

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
          // Um 401 numa rota autenticada significa sessão inválida/
          // expirada — força logout + regresso ao login. O authGuard já
          // apanha isto ao mudar de página, mas não cobre o caso de o
          // token expirar enquanto o utilizador está parado numa página
          // (ex.: o polling da contagem de notificações continua a
          // correr de 60 em 60s). Exclui o próprio POST de login: aí um
          // 401 é só "password errada", tratado como loginFalhou, não
          // como sessão a expirar.
          const ehPedidoDeLogin = req.url.includes('/api/v1/auth/login');
          if (erro.status === 401 && !ehPedidoDeLogin) {
            store.dispatch(sessaoExpirada());
          }
          return throwError(() => erro);
        })
      );
    })
  );
};
