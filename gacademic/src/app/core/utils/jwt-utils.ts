/**
 * Descodifica só o payload de um JWT (sem validar a assinatura — isso é
 * sempre feito no back-end; aqui só serve para decisões de UI, como
 * saber se vale a pena sequer tentar navegar com este token ou já
 * mandar direto para o login).
 */
function descodificarPayload(token: string): Record<string, unknown> | null {
  try {
    const [, payloadBase64] = token.split('.');
    if (!payloadBase64) return null;
    const normalizado = payloadBase64.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(normalizado));
  } catch {
    return null;
  }
}

/** true se o token não existir, estiver malformado, ou já tiver passado do "exp". */
export function tokenExpirado(token: string | null | undefined): boolean {
  if (!token) return true;
  const payload = descodificarPayload(token);
  const exp = payload?.['exp'];
  if (typeof exp !== 'number') return true;
  return Date.now() >= exp * 1000;
}
