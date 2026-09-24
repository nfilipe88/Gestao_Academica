import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, UrlTree, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { provideStore, Store } from '@ngrx/store';
import { firstValueFrom, isObservable, Observable } from 'rxjs';
import { authReducer } from '../../store/auth/auth.reducer';
import { configuracoesReducer } from '../../store/configuracoes/configuracoes.reducer';
import { loginSuccess } from '../../store/auth/auth.actions';
import { carregarConfiguracaoSucesso } from '../../store/configuracoes/configuracoes.actions';
import { CONFIGURACAO_INICIAL } from '../../store/configuracoes/configuracoes.models';
import { selectAuthError } from '../../store/auth/auth.selectors';
import { perfilGuard } from './perfil.guard';
import { authGuard } from './auth.guard';
import { termosGuard } from './termos.guard';
import { ALUNO, GESTOR, instalarLocalStorageFalso, jwtFalso } from '../../testing/ajudas';

async function correr(guard: any, url = '/destino'): Promise<boolean | string> {
  const estado = { url } as RouterStateSnapshot;
  const resultado = TestBed.runInInjectionContext(() => guard({} as ActivatedRouteSnapshot, estado));
  const valor = isObservable(resultado) ? await firstValueFrom(resultado as Observable<unknown>) : await resultado;
  return valor instanceof UrlTree ? TestBed.inject(Router).serializeUrl(valor) : (valor as boolean);
}

function entrar(utilizador: any, token = jwtFalso(600)) {
  TestBed.inject(Store).dispatch(loginSuccess({ token, usuario: utilizador }));
}

describe('guards', () => {
  beforeEach(() => {
    instalarLocalStorageFalso();
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideStore({ auth: authReducer, configuracoes: configuracoesReducer })],
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  describe('perfilGuard', () => {
    it('deixa passar um perfil permitido', async () => {
      entrar(GESTOR);
      expect(await correr(perfilGuard('GESTOR', 'SECRETARIA'))).toBe(true);
    });

    it('manda um aluno bloqueado para o Portal e não para o dashboard', async () => {
      entrar(ALUNO);
      expect(await correr(perfilGuard('GESTOR'))).toBe('/portal');
    });

    it('manda o Super Admin bloqueado para /admin', async () => {
      entrar({ ...GESTOR, perfil_acesso: 'SUPER_ADMIN' });
      expect(await correr(perfilGuard('GESTOR'))).toBe('/admin');
    });

    it('sem perfil cai no dashboard', async () => {
      expect(await correr(perfilGuard('GESTOR'))).toBe('/dashboard');
    });
  });

  describe('authGuard', () => {
    it('sem token manda para o login guardando o destino', async () => {
      expect(await correr(authGuard, '/financeiro')).toBe('/login?returnUrl=%2Ffinanceiro');
    });

    it('com token válido deixa passar', async () => {
      entrar(GESTOR, jwtFalso(600));
      expect(await correr(authGuard)).toBe(true);
    });

    it('com token expirado limpa a sessão, mostra a mensagem e vai para o login', async () => {
      entrar(GESTOR, jwtFalso(-60));
      expect(await correr(authGuard, '/alunos')).toBe('/login?returnUrl=%2Falunos');
      expect(await firstValueFrom(TestBed.inject(Store).select(selectAuthError))).toContain('expirou');
    });
  });

  describe('termosGuard', () => {
    function configuracaoCarregada(termos: string | null) {
      TestBed.inject(Store).dispatch(carregarConfiguracaoSucesso({
        configuracao: { ...CONFIGURACAO_INICIAL, termos_aceites_em: termos },
      }));
    }

    it('o Gestor sem termos aceites é levado para /aceitar-termos', async () => {
      entrar(GESTOR);
      configuracaoCarregada(null);
      expect(await correr(termosGuard, '/dashboard')).toBe('/aceitar-termos');
    });

    it('o Gestor com termos aceites passa', async () => {
      entrar(GESTOR);
      configuracaoCarregada('2026-09-24T10:00:00Z');
      expect(await correr(termosGuard, '/dashboard')).toBe(true);
    });

    it('a própria página de aceitação nunca é bloqueada', async () => {
      entrar(GESTOR);
      configuracaoCarregada(null);
      expect(await correr(termosGuard, '/aceitar-termos')).toBe(true);
    });

    it('perfis que não são o Gestor não são obrigados a aceitar', async () => {
      entrar(ALUNO);
      expect(await correr(termosGuard, '/portal')).toBe(true);
    });
  });
});
