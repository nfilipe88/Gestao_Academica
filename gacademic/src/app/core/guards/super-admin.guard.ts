import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { map, take } from 'rxjs';
import { selectIsSuperAdmin } from '../../store/auth/auth.selectors';

// authGuard (aplicado ao pai) já garante sessão válida — este guard só
// acrescenta a verificação de perfil, para rotas exclusivas do Super
// Admin (ex.: /admin/permissoes) não ficarem a depender só do link do
// sidebar estar escondido. Quem não for SUPER_ADMIN é mandado para o
// dashboard normal em vez de ver uma página vazia ou um erro.
export const superAdminGuard: CanActivateFn = () => {
  const store = inject(Store);
  const router = inject(Router);

  return store.select(selectIsSuperAdmin).pipe(
    take(1),
    map(isSuperAdmin => isSuperAdmin || router.createUrlTree(['/dashboard']))
  );
};
