import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { filter, map, switchMap, take } from 'rxjs';
import { selectIsGestor } from '../../store/auth/auth.selectors';
import { carregarConfiguracao } from '../../store/configuracoes/configuracoes.actions';
import { selectConfiguracao, selectConfiguracoesCarregada } from '../../store/configuracoes/configuracoes.selector';

// Escolas criadas pelo Super Admin nascem sem aceitação da Política de
// Privacidade/Termos (ele não pode aceitar em nome da escola): no primeiro
// acesso o Gestor é encaminhado para /aceitar-termos, antes de qualquer
// outra página. Escolas que se registaram sozinhas já aceitaram no registo.
// Só o Gestor é obrigado (é quem responde pela escola e quem o back-end
// deixa aceitar); os restantes perfis passam sempre.
export const termosGuard: CanActivateFn = (route, state) => {
  const store = inject(Store);
  const router = inject(Router);

  if (state.url.startsWith('/aceitar-termos')) return true;

  return store.select(selectIsGestor).pipe(
    take(1),
    switchMap(isGestor => {
      if (!isGestor) return [true];
      return store.select(selectConfiguracoesCarregada).pipe(
        take(1),
        switchMap(carregada => {
          if (!carregada) store.dispatch(carregarConfiguracao());
          return store.select(selectConfiguracoesCarregada).pipe(filter(c => c), take(1));
        }),
        switchMap(() => store.select(selectConfiguracao).pipe(take(1))),
        map(config => config.termos_aceites_em ? true : router.createUrlTree(['/aceitar-termos']))
      );
    })
  );
};
