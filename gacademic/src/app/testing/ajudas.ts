import { vi } from 'vitest';

/**
 * localStorage em memória. O Node 22+ expõe um `localStorage` experimental que
 * pode sobrepor-se ao do jsdom, por isso os testes usam sempre este duplo
 * (ver app.spec.ts para a explicação completa).
 */
export function instalarLocalStorageFalso(): Storage {
  const dados = new Map<string, string>();
  const falso = {
    getItem: (chave: string) => dados.get(chave) ?? null,
    setItem: (chave: string, valor: string) => { dados.set(chave, valor); },
    removeItem: (chave: string) => { dados.delete(chave); },
    clear: () => { dados.clear(); },
    key: (indice: number) => Array.from(dados.keys())[indice] ?? null,
    get length() { return dados.size; },
  } as Storage;
  vi.stubGlobal('localStorage', falso);
  return falso;
}

/** JWT só com payload {exp} — suficiente para tokenExpirado(); a assinatura nunca é validada no front-end. */
export function jwtFalso(segundosAteExpirar: number): string {
  const b64 = (o: object) => btoa(JSON.stringify(o)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  return `${b64({ alg: 'HS256' })}.${b64({ exp: Math.floor(Date.now() / 1000) + segundosAteExpirar })}.assinatura`;
}

export const GESTOR = { id: 'u1', tenant_id: 't1', nome_completo: 'Gestor', perfil_acesso: 'GESTOR' };
export const ALUNO = { id: 'u2', tenant_id: 't1', nome_completo: 'Aluno', perfil_acesso: 'ALUNO' };
