import { DashboardHomeComponent } from './features/academico/dashboard-home.component/dashboard-home.component';
import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { guestGuard } from './core/guards/guest.guard';
import { superAdminGuard } from './core/guards/super-admin.guard';
import { permissoesGuard } from './core/guards/permissoes.guard';
import { publicoMatchGuard } from './core/guards/publico.guard';

export const routes: Routes = [
  // ==========================================
  // SITE PÚBLICO (apresentação da plataforma) — sempre acessível,
  // mesmo com sessão iniciada, exceto a página inicial em si: quem já
  // está autenticado é encaminhado para o Dashboard em vez da Landing
  // (ver publicoMatchGuard — canMatch, não canActivate, para poder
  // "cair" para o shell autenticado abaixo em vez de bloquear).
  // ==========================================
  {
    path: '',
    canMatch: [publicoMatchGuard],
    loadComponent: () => import('./shared/components/public-layout/public-layout.component/public-layout.component').then((m) => m.PublicLayoutComponent),
    children: [
      { path: '', loadComponent: () => import('./features/public/landing/landing.component/landing.component').then((m) => m.LandingComponent) },
    ]
  },
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
  {
    path: 'esqueci-senha',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/public/esqueci-senha/esqueci-senha.component/esqueci-senha.component').then((m) => m.EsqueciSenhaComponent)
  },

  // ==========================================
  // ROTAS PÚBLICAS (sem guestGuard — não são sobre estar "deslogado")
  // ==========================================
  {
    path: 'captar/:tenantId',
    loadComponent: () => import('./features/public/captar-lead/captar-lead.component/captar-lead.component').then((m) => m.CaptarLeadComponent)
  },
  {
    // Página pública de UMA escola (marketing/angariação de alunos) —
    // fora de PublicLayoutComponent de propósito: mostra a marca da
    // ESCOLA (logótipo, nome), não a da plataforma. Ver docstring do componente.
    path: 'escola/:tenantId',
    loadComponent: () => import('./features/public/escola/escola.component/escola.component').then((m) => m.EscolaComponent)
  },
  {
    // Assistente de matrícula self-service (candidatura em 4 passos,
    // com documentos) — rota própria, não uma secção dentro de
    // escola.component: é um fluxo utilitário, não uma página de
    // marketing, por isso não varia por modelo (ver
    // features/public/matricula/matricula-wizard.component).
    path: 'escola/:tenantId/matricula',
    loadComponent: () => import('./features/public/matricula/matricula-wizard.component/matricula-wizard.component').then((m) => m.MatriculaWizardComponent)
  },
  {
    // Acedida a partir do link de e-mail — tem de funcionar mesmo com
    // uma sessão antiga aberta noutro separador, por isso sem
    // guestGuard (ver docstring do componente).
    path: 'redefinir-senha',
    loadComponent: () => import('./features/public/redefinir-senha/redefinir-senha.component/redefinir-senha.component').then((m) => m.RedefinirSenhaComponent)
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
        path: 'rematricula',
        loadComponent: () => import('./features/academico/rematricula/rematricula.component/rematricula.component').then((m) => m.RematriculaComponent)
      },
      {
        path: 'alunos',
        loadComponent: () => import('./features/pessoas/alunos.component/alunos.component').then((m) => m.AlunosComponent)
      },
      {
        path: 'professores',
        loadComponent: () => import('./features/pessoas/professores.component/professores.component').then((m) => m.ProfessoresComponent)
      },
      {
        path: 'comunicacoes',
        loadComponent: () => import('./features/comunicacoes/comunicacoes.component/comunicacoes.component').then((m) => m.ComunicacoesComponent)
      },
      {
        path: 'diario',
        loadComponent: () => import('./features/diario/diario.component/diario.component').then((m) => m.DiarioComponent)
      },
      {
        path: 'financeiro',
        loadComponent: () => import('./features/financeiro/financeiro.component/financeiro.component').then((m) => m.FinanceiroComponent)
      },
      {
        path: 'propinas',
        loadComponent: () => import('./features/propinas/propinas.component/propinas.component').then((m) => m.PropinasComponent)
      },
      {
        path: 'crm',
        loadComponent: () => import('./features/crm/crm.component/crm.component').then((m) => m.CrmComponent)
      },
      {
        path: 'horarios',
        loadComponent: () => import('./features/horarios/horarios.component/horarios.component').then((m) => m.HorariosComponent)
      },
      {
        path: 'portal',
        loadComponent: () => import('./features/portal/portal.component/portal.component').then((m) => m.PortalComponent)
      },
      {
        path: 'admin',
        loadComponent: () => import('./features/admin/admin.component/admin.component').then((m) => m.AdminComponent)
      },
      {
        path: 'admin/permissoes',
        canActivate: [permissoesGuard],
        loadComponent: () => import('./features/admin/permissoes.component/permissoes.component').then((m) => m.PermissoesComponent)
      },
      {
        // Sem guard próprio (mesmo padrão de 'admin' acima) — o link só
        // aparece no menu para SUPER_ADMIN, e a API já recusa (403)
        // qualquer outro perfil em /api/v1/admin/tickets.
        path: 'admin/tickets',
        loadComponent: () => import('./features/admin/tickets.component/tickets.component').then((m) => m.TicketsComponent)
      },
      {
        path: 'tarefas',
        loadComponent: () => import('./features/tarefas/tarefas.component/tarefas.component').then((m) => m.TarefasComponent)
      },
      {
        path: 'documentos',
        loadComponent: () => import('./features/documentos/documentos.component/documentos.component').then((m) => m.DocumentosComponent)
      },
      {
        path: 'transferencias',
        loadComponent: () => import('./features/transferencias/transferencias.component/transferencias.component').then((m) => m.TransferenciasComponent)
      },
      {
        path: 'indicadores',
        loadComponent: () => import('./features/indicadores/indicadores.component/indicadores.component').then((m) => m.IndicadoresComponent)
      },
      {
        path: 'estatisticas',
        loadComponent: () => import('./features/estatisticas/estatisticas.component/estatisticas.component').then((m) => m.EstatisticasComponent)
      },
      {
        path: 'configuracoes',
        loadComponent: () => import('./features/configuracoes/configuracoes.component/configuracoes.component').then((m) => m.ConfiguracoesComponent)
      },
      {
        path: 'acessos',
        loadComponent: () => import('./features/usuarios/acessos.component/acessos.component').then((m) => m.AcessosComponent)
      },
      {
        path: 'auditoria',
        loadComponent: () => import('./features/auditoria/auditoria.component/auditoria.component').then((m) => m.AuditoriaComponent)
      },
      {
        path: 'suporte',
        loadComponent: () => import('./features/suporte/suporte.component/suporte.component').then((m) => m.SuporteComponent)
      },
      {
        // Sem RBAC — qualquer utilizador autenticado gere a própria
        // conta (ver app/api/v1/perfil.py, sem exigir_perfil).
        path: 'perfil',
        loadComponent: () => import('./features/perfil/perfil.component/perfil.component').then((m) => m.PerfilComponent)
      },
      // Futuras rotas académicas entrarão aqui...
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
    ]
  },

  // Restantes páginas do site público — DEPOIS do shell autenticado de
  // propósito: como o próprio path é '' e a "/" já foi decidida acima
  // (Landing vs Dashboard), esta entrada só entra em jogo quando o URL
  // tem mais segmentos (/funcionalidades, /precos); se viesse antes do
  // shell, "roubava" sempre a "/" a quem tem sessão (o Router aceita um
  // path:'' sem filhos correspondentes como válido, com o outlet vazio,
  // quando não sobra URL nenhum por consumir — foi o bug visto ao testar).
  {
    path: '',
    loadComponent: () => import('./shared/components/public-layout/public-layout.component/public-layout.component').then((m) => m.PublicLayoutComponent),
    children: [
      { path: 'funcionalidades', loadComponent: () => import('./features/public/funcionalidades/funcionalidades.component/funcionalidades.component').then((m) => m.FuncionalidadesComponent) },
      { path: 'precos', loadComponent: () => import('./features/public/precos/precos.component/precos.component').then((m) => m.PrecosComponent) },
      { path: 'contacto', loadComponent: () => import('./features/public/contacto/contacto.component/contacto.component').then((m) => m.ContactoComponent) },
    ]
  },

  // Fallback (Página não encontrada)
  { path: '**', redirectTo: 'login' }
];
