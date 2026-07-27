import { CanActivateFn, Router } from '@angular/router';
import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Store } from '@ngrx/store';
import { selectToken } from '../../store/auth/auth.selectors';
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

      if (token || tokenLocal) {
        // Já está logado? Vai direto para o painel
        return router.createUrlTree(['/dashboard']);
      }
      return true; // Não está logado, pode ver o ecrã de login
    })
  );
};
