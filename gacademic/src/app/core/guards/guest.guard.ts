import { CanActivateFn, Router } from '@angular/router';
import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Store } from '@ngrx/store';
import { selectToken } from '../../store/auth/auth.selectors';
import { tokenExpirado } from '../utils/jwt-utils';
import { map, take } from 'rxjs';

export const guestGuard: CanActivateFn = (route, state) => {
  const store = inject(Store);
  const router = inject(Router);
  const platformId = inject(PLATFORM_ID);
  const isBrowser = isPlatformBrowser(platformId);

  return store.select(selectToken).pipe(
    take(1),
    map(token => {
      // const tokenLocal = isBrowser ? localStorage.getItem('saas_access_token') : null;

      // Verifica o localStorage de forma segura
      let tokenLocal = null;
      if (isPlatformBrowser(platformId)) {
        tokenLocal = localStorage.getItem('saas_access_token');
      }

      const tokenAtual = token || tokenLocal;

      // Um token expirado não conta como "já logado" — sem isto, quem
      // chega ao /login com uma sessão expirada era mandado de volta
      // para /dashboard, que por sua vez o devolvia ao /login (via
      // authGuard), um ciclo desnecessário.
      if (tokenAtual && !tokenExpirado(tokenAtual)) {
        // Já está logado? Volta ao destino original (returnUrl), se
        // veio de um redirecionamento do authGuard; senão vai para o
        // dashboard por omissão.
        const returnUrl = route.queryParamMap.get('returnUrl');
        return returnUrl ? router.parseUrl(returnUrl) : router.createUrlTree(['/dashboard']);
      }
      return true; // Não está logado, pode ver o ecrã de login
    })
  );
};
