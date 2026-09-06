import { isPlatformBrowser } from '@angular/common';

// Mesma forma de core/utils/armazenamento-sessao.ts, mas sobre
// localStorage — para preferências que devem durar entre sessões (não
// só na aba/separador atual), como "já vi as dicas do dashboard, não
// mostres mais" (ver dashboard-home.component/portal.component).
export const CHAVE_LOCAL_DICAS_DASHBOARD_FECHADAS = 'saas_dicas_dashboard_fechadas';
export const CHAVE_LOCAL_DICAS_PORTAL_FECHADAS = 'saas_dicas_portal_fechadas';

// Wrapper seguro sobre localStorage — mesma cautela de SSR (Angular
// Universal: localStorage não existe no processo de servidor) e de
// modo privado/storage bloqueado (lança exceção em vez de devolver
// null em alguns browsers) já usada em armazenamento-sessao.ts —
// falha em silêncio, a app continua a funcionar, só sem lembrar a
// preferência entre sessões.
export function lerLocal(platformId: object, chave: string): string | null {
  if (!isPlatformBrowser(platformId)) return null;
  try {
    return localStorage.getItem(chave);
  } catch {
    return null;
  }
}

export function guardarLocal(platformId: object, chave: string, valor: string | null): void {
  if (!isPlatformBrowser(platformId)) return;
  try {
    if (valor) {
      localStorage.setItem(chave, valor);
    } else {
      localStorage.removeItem(chave);
    }
  } catch {
    // Ignora de propósito — ver nota acima.
  }
}
