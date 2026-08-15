import { CanActivateFn, Router } from '@angular/router';
import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Store } from '@ngrx/store';
import { selectToken } from '../../store/auth/auth.selectors';
import { sessaoExpirada } from '../../store/auth/auth.actions';
import { tokenExpirado } from '../utils/jwt-utils';
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

      const tokenAtual = token || tokenLocal;

      // Um token presente mas expirado NÃO passa: sem isto, um utilizador
      // com sessão expirada continuava a navegar livremente pelo menu
      // (o guard só via "existe token", nunca "ainda é válido") e só
      // descobria o problema quando um pedido à API falhasse. Verificar
      // aqui bloqueia a navegação logo no clique.
      if (tokenAtual && !tokenExpirado(tokenAtual)) {
        return true; // Tem passe livre
      }

      if (tokenAtual) {
        // Existe um token, mas já expirou — limpa a sessão (localStorage
        // + store) e mostra "sessão expirada" no ecrã de login.
        store.dispatch(sessaoExpirada());
      }

      // Se não tem token (ou acabou de ser limpo acima), é expulso para o
      // ecrã de login, mas guardamos o destino pretendido em returnUrl.
      // Sem isto, um F5/link direto numa rota protegida (ex.: /cursos)
      // perde-se sempre: o SSR não consegue ler o localStorage no
      // primeiro pedido, por isso este guard nega no servidor, e o
      // utilizador acaba sempre em /dashboard assim que o guestGuard
      // confirma a sessão no browser (ver guest.guard.ts).
      return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
    })
  );
};
