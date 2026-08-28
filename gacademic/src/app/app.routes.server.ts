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
  {
    path: '**',
    renderMode: RenderMode.Prerender
  }
];
