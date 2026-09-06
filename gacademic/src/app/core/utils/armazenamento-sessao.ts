import { isPlatformBrowser } from '@angular/common';

// Chaves partilhadas — centralizadas aqui (em vez de uma string
// duplicada em cada sítio que lê/escreve) para o logout (ver
// store/auth/auth.effects.ts::clearAuthData$) conseguir limpar tudo
// de uma vez; sem isso, a seleção de um utilizador ficava visível para
// o próximo a iniciar sessão no mesmo separador do browser.
export const CHAVE_SESSAO_FINANCEIRO_ALUNO = 'financeiro_aluno_id';
export const CHAVE_SESSAO_FINANCEIRO_MATRICULA = 'financeiro_matricula_id';
export const CHAVE_SESSAO_PORTAL_EDUCANDO = 'portal_educando_id';

// Wrapper seguro sobre sessionStorage — a app usa Angular Universal
// (SSR): sessionStorage não existe no processo de servidor. Na
// prática as rotas que usam isto (Financeiro, Portal) só renderizam
// depois do authGuard confirmar a sessão no browser (ver
// core/guards/auth.guard.ts), mas mantém-se a mesma cautela já usada
// lá para localStorage — nunca aceder diretamente sem confirmar a
// plataforma primeiro. Também protegido contra modo privado/storage
// bloqueado (lança exceção em vez de simplesmente devolver null em
// alguns browsers) — falha em silêncio, a app continua a funcionar,
// só sem lembrar a seleção entre navegações.
export function lerSessao(platformId: object, chave: string): string | null {
  if (!isPlatformBrowser(platformId)) return null;
  try {
    return sessionStorage.getItem(chave);
  } catch {
    return null;
  }
}

export function guardarSessao(platformId: object, chave: string, valor: string | null): void {
  if (!isPlatformBrowser(platformId)) return;
  try {
    if (valor) {
      sessionStorage.setItem(chave, valor);
    } else {
      sessionStorage.removeItem(chave);
    }
  } catch {
    // Ignora de propósito — ver nota acima.
  }
}
