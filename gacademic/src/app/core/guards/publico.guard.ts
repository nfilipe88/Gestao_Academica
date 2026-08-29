import { CanMatchFn, Router } from '@angular/router';
import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Store } from '@ngrx/store';
import { selectToken } from '../../store/auth/auth.selectors';
import { tokenExpirado } from '../utils/jwt-utils';
import { map, take } from 'rxjs';

/**
 * canMatch (não canActivate) de propósito: quando devolve false, o
 * Router tenta a PRÓXIMA rota da lista que também bata com o mesmo
 * caminho (path: '') — aqui, o shell autenticado (dashboard-layout,
 * ver app.routes.ts) — em vez de bloquear a navegação. É o que permite
 * a página inicial "/" mostrar a Landing a um visitante e o Dashboard
 * a quem já tem sessão, sem duplicar a rota "/" nem redirecionar com
 * flash visível.
 *
 * Só aplicado à Landing em si (path: '' dentro do grupo público) —
 * as outras páginas de apresentação (Funcionalidades, Preços) ficam
 * sempre acessíveis, mesmo com sessão iniciada (ex.: alguém partilhou
 * um link de /precos).
 */
export const publicoMatchGuard: CanMatchFn = () => {
  const store = inject(Store);
  const platformId = inject(PLATFORM_ID);

  return store.select(selectToken).pipe(
    take(1),
    map(token => {
      let tokenLocal = null;
      if (isPlatformBrowser(platformId)) {
        tokenLocal = localStorage.getItem('saas_access_token');
      }
      const tokenAtual = token || tokenLocal;
      return !(tokenAtual && !tokenExpirado(tokenAtual));
    })
  );
};
