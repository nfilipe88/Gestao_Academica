import { DashboardHomeComponent } from './features/academico/dashboard-home.component/dashboard-home.component';
import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { guestGuard } from './core/guards/guest.guard';

export const routes: Routes = [
    // ==========================================
  // ROTAS PÚBLICAS (Apenas para não logados)
  // ==========================================
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent:() => import('./features/public/login/login.component/login.component').then((m) => m.LoginComponent)
  },
  {
    path: 'registo',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/public/registo/registo.component/registo.component').then((m) => m.RegistoComponent)
  },

  // ==========================================
  // ROTAS PROTEGIDAS (Exigem Autenticação)
  // ==========================================
  {
    path: '',
    canActivate: [authGuard], // Bloqueia tudo o que está dentro destes filhos
    loadComponent: () => import('./shared/components/dashboard-layout/dashboard-layout.component/dashboard-layout.component').then((m) => m.DashboardLayoutComponent),
    children: [
      {
        path: 'dashboard',
        // Componente temporário só para preencher o vazio
        loadComponent: () => import('./features/academico/dashboard-home.component/dashboard-home.component').then((m) => m.DashboardHomeComponent)
      },
      {
        path: 'cursos',
        loadComponent: () => import('./features/academico/cursos/cursos.component/cursos.component').then((m) => m.CursosComponent)
      },
      {
        path: 'turmas',
        loadComponent: () => import('./features/academico/turmas/turmas.component/turmas.component').then((m) => m.TurmasComponent)
      },
      {
        path: 'alunos',
        loadComponent: () => import('./features/pessoas/alunos.component/alunos.component').then((m) => m.AlunosComponent)
      },
      {
        path: 'professores',
        loadComponent: () => import('./features/pessoas/professores.component/professores.component').then((m) => m.ProfessoresComponent)
      },
      // Futuras rotas académicas entrarão aqui...
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
    ]
  },

  // Fallback (Página não encontrada)
  { path: '**', redirectTo: 'login' }
];
