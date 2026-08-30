import { RenderMode, ServerRoute } from '@angular/ssr';

export const serverRoutes: ServerRoute[] = [
  // Página pública de captação de Lead (CRM) — dinâmica por escola
  // (:tenantId só existe em runtime, escolas novas surgem depois de
  // cada build), por isso não pode ser pré-renderizada como o resto:
  // isso é precisamente o que fazia `ng build` (produção) falhar com
  // "uses prerendering and includes parameters, but getPrerenderParams
  // is missing". Renderizada no servidor a cada pedido em vez de fixada
  // em build-time.
  {
    path: 'captar/:tenantId',
    renderMode: RenderMode.Server
  },
  // Mesma razão da rota acima — :tenantId dinâmico, e busca dados reais
  // à API (GET /api/v1/public/escola/:tenantId) no ngOnInit.
  {
    path: 'escola/:tenantId',
    renderMode: RenderMode.Server
  },
  // Assistente de matrícula self-service — mesma razão: :tenantId
  // dinâmico e dados reais buscados no ngOnInit.
  {
    path: 'escola/:tenantId/matricula',
    renderMode: RenderMode.Server
  },
  // Página de Preços busca os planos ativos à API (GET /api/v1/public/planos)
  // no ngOnInit — dados que mudam sem novo build (o Super Admin cria/edita
  // planos em runtime). Pré-renderizar isto fixava os preços no que
  // existia no momento do build (ou falhava logo o build, se o backend
  // não estivesse acessível durante o `ng build`) — em vez disso,
  // renderizada no servidor a cada pedido, mesmo raciocínio da rota acima.
  {
    path: 'precos',
    renderMode: RenderMode.Server
  },
  {
    path: '**',
    renderMode: RenderMode.Prerender
  }
];
