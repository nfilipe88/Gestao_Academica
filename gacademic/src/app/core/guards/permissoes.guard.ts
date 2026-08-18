import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { map, take } from 'rxjs';
import { selectPodeEditarPermissoes } from '../../store/auth/auth.selectors';

// /admin/permissoes é editável pelo SUPER_ADMIN e pelo GESTOR (ver
// api/v1/permissoes.py::_PODE_ACEDER) — diferente de superAdminGuard,
// que continua reservado a rotas exclusivas do Super Admin.
export const permissoesGuard: CanActivateFn = () => {
  const store = inject(Store);
  const router = inject(Router);

  return store.select(selectPodeEditarPermissoes).pipe(
    take(1),
    map(podeEditar => podeEditar || router.createUrlTree(['/dashboard']))
  );
};
