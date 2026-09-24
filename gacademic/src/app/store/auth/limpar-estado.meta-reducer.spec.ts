import { describe, expect, it } from 'vitest';
import { ActionReducer } from '@ngrx/store';
import { limparEstadoNoLogout } from './limpar-estado.meta-reducer';
import { loginSuccess, logout, sessaoExpirada } from './auth.actions';
import { authReducer } from './auth.reducer';

// Dois slices reais e simples: a auth e um "financeiro" fictício que guarda dados do utilizador.
interface Estado { auth: ReturnType<typeof authReducer>; dados: string[]; }
const reducerRaiz: ActionReducer<Estado> = (estado, acao) => ({
  auth: authReducer(estado?.auth, acao),
  dados: acao.type === 'carregar' ? ['fatura confidencial'] : (estado?.dados ?? []),
});
const reducer = limparEstadoNoLogout(reducerRaiz);

function comSessaoIniciada(): Estado {
  let estado = reducer(undefined, { type: '@@init' });
  estado = reducer(estado, loginSuccess({ token: 't', usuario: { id: 'u1', perfil_acesso: 'GESTOR' } as any }));
  return reducer(estado, { type: 'carregar' });
}

describe('limparEstadoNoLogout', () => {
  it('no logout repõe todos os slices ao estado inicial', () => {
    const antes = comSessaoIniciada();
    expect(antes.dados.length).toBe(1);
    expect(antes.auth.isAuthenticated).toBe(true);

    const depois = reducer(antes, logout());
    expect(depois.dados).toEqual([]);
    expect(depois.auth.token).toBeNull();
    expect(depois.auth.usuario).toBeNull();
    expect(depois.auth.isAuthenticated).toBe(false);
  });

  it('na sessão expirada limpa tudo mas mantém a mensagem para o ecrã de login', () => {
    const depois = reducer(comSessaoIniciada(), sessaoExpirada());
    expect(depois.dados).toEqual([]);
    expect(depois.auth.token).toBeNull();
    expect(depois.auth.erro).toContain('expirou');
  });

  it('não mexe no estado em ações normais', () => {
    const antes = comSessaoIniciada();
    const depois = reducer(antes, { type: 'qualquer-outra' });
    expect(depois.dados).toEqual(antes.dados);
    expect(depois.auth.token).toBe('t');
  });
});
