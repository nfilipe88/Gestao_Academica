import { RenderMode, ServerRoute } from '@angular/ssr';

/**
 * Como cada rota é servida:
 *  - Server: a cada pedido, no servidor — páginas públicas com dados que mudam
 *    sem novo build ou dependem de :tenantId (escolas novas surgem em runtime).
 *  - Prerender: HTML fixado no build — só páginas públicas estáticas.
 *  - Client: só o casco vazio (index.csr.html); a app arranca no browser e o
 *    authGuard decide com a sessão guardada no localStorage.
 *
 * TODAS as rotas autenticadas (dashboard, alunos, financeiro, portal, admin…)
 * têm de ser Client. Pré-renderizá-las não faz sentido: o servidor não tem
 * sessão (localStorage só existe no browser), por isso o authGuard falhava no
 * build e o HTML gerado era só uma página "Redirecting to /login" — quem tinha
 * sessão e carregava F5 em /dashboard passava por uma ida ao login e volta. E
 * se algum dia se ativar a hidratação (provideClientHydration), HTML fixado no
 * build diferente da árvore autenticada seria um "hydration mismatch". Hoje a
 * hidratação NÃO está ativa (o browser volta a desenhar a página por cima do
 * HTML do servidor), mas ficar Client evita o problema à partida.
 *
 * Por omissão (`**`) uma rota nova é Client — seguro para qualquer página
 * autenticada; uma página pública nova que queira SSR/prerender tem de ser
 * acrescentada à lista abaixo de propósito.
 */
export const serverRoutes: ServerRoute[] = [
  // Páginas públicas dinâmicas por escola (:tenantId só existe em runtime e busca dados à API).
  { path: 'captar/:tenantId', renderMode: RenderMode.Server },
  { path: 'escola/:tenantId', renderMode: RenderMode.Server },
  { path: 'escola/:tenantId/matricula', renderMode: RenderMode.Server },
  // Os planos vêm da API (GET /api/v1/public/planos) e o Super Admin altera-os sem novo build.
  { path: 'precos', renderMode: RenderMode.Server },

  // Páginas públicas estáticas — seguras de fixar no build.
  { path: '', renderMode: RenderMode.Prerender },
  { path: 'login', renderMode: RenderMode.Prerender },
  { path: 'registo', renderMode: RenderMode.Prerender },
  { path: 'esqueci-senha', renderMode: RenderMode.Prerender },
  { path: 'redefinir-senha', renderMode: RenderMode.Prerender },
  { path: 'ativar-conta', renderMode: RenderMode.Prerender },
  { path: 'funcionalidades', renderMode: RenderMode.Prerender },
  { path: 'contacto', renderMode: RenderMode.Prerender },
  { path: 'privacidade', renderMode: RenderMode.Prerender },

  // Tudo o resto (todas as áreas autenticadas): só no browser.
  { path: '**', renderMode: RenderMode.Client },
];
