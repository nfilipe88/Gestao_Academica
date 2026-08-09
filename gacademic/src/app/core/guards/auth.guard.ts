import { CanActivateFn, Router } from '@angular/router';
import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Store } from '@ngrx/store';
import { selectToken } from '../../store/auth/auth.selectors';
import { map, take } from 'rxjs';

export const authGuard: CanActivateFn = (route, state) => {
  const store = inject(Store);
  const router = inject(Router);
  const platformId = inject(PLATFORM_ID);
  const isBrowser = isPlatformBrowser(platformId);

  // Lemos o token do Redux de forma reativa
  return store.select(selectToken).pipe(
    take(1),
    map(token => {
      // Fallback para o localStorage só existe no browser (não no SSR)
      // const tokenLocal = isBrowser ? localStorage.getItem('saas_access_token') : null;

      // Verifica o localStorage de forma segura
      let tokenLocal = null;
      if (isPlatformBrowser(platformId)) {
        tokenLocal = localStorage.getItem('saas_access_token');
      }
      
      if (token || tokenLocal) {
        return true; // Tem passe livre
      }

      // Se não tem token, é expulso para o ecrã de login, mas guardamos
      // o destino pretendido em returnUrl. Sem isto, um F5/link direto
      // numa rota protegida (ex.: /cursos) perde-se sempre: o SSR não
      // consegue ler o localStorage no primeiro pedido, por isso este
      // guard nega no servidor, e o utilizador acaba sempre em
      // /dashboard assim que o guestGuard confirma a sessão no browser
      // (ver guest.guard.ts).
      return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
    })
  );
};
