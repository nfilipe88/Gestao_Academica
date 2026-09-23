import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { map, take } from 'rxjs';
import { selectPerfilAcesso } from '../../store/auth/auth.selectors';

// "Página inicial" de cada perfil — para onde mandar quem é bloqueado
// por um perfilGuard, em vez de sempre '/dashboard' (que os próprios
// ALUNO/RESPONSAVEL/SUPER_ADMIN não conseguem abrir, ver app.routes.ts).
const _HOME_POR_PERFIL: Record<string, string> = {
  SUPER_ADMIN: '/admin',
  ALUNO: '/portal',
  RESPONSAVEL: '/portal',
  GESTOR: '/dashboard',
  SECRETARIA: '/dashboard',
  PROFESSOR: '/dashboard',
};

// authGuard (aplicado ao pai, ver app.routes.ts) já garante sessão
// válida — este guard só acrescenta a verificação de perfil, mesma
// razão de superAdminGuard/permissoesGuard, generalizada para não
// precisar de um ficheiro novo por combinação de perfis. Sem isto, o
// link só desaparecia do menu lateral (dashboard-layout.component.html)
// mas navegar direto ao URL continuava a "entrar" na página, só para
// cada pedido à API dentro dela falhar com 403 — um ecrã em branco/
// quebrado em vez de um redireccionamento limpo.
export function perfilGuard(...perfisPermitidos: string[]): CanActivateFn {
  return () => {
    const store = inject(Store);
    const router = inject(Router);

    return store.select(selectPerfilAcesso).pipe(
      take(1),
      map(perfil => {
        if (perfil && perfisPermitidos.includes(perfil)) return true;
        return router.createUrlTree([(perfil && _HOME_POR_PERFIL[perfil]) || '/dashboard']);
      })
    );
  };
}
