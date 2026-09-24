import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideStore, Store } from '@ngrx/store';
import { firstValueFrom } from 'rxjs';
import { jwtInterceptor } from './jwt.interceptor';
import { authReducer } from '../../store/auth/auth.reducer';
import { loginSuccess } from '../../store/auth/auth.actions';
import { selectAuthError, selectToken } from '../../store/auth/auth.selectors';
import { GESTOR, instalarLocalStorageFalso } from '../../testing/ajudas';

describe('jwtInterceptor', () => {
  let http: HttpClient;
  let backend: HttpTestingController;
  let store: Store;

  beforeEach(() => {
    instalarLocalStorageFalso();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([jwtInterceptor])),
        provideHttpClientTesting(),
        provideStore({ auth: authReducer }),
      ],
    });
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
    store = TestBed.inject(Store);
    store.dispatch(loginSuccess({ token: 'acesso-1', usuario: GESTOR }));
  });

  afterEach(() => {
    backend.verify();
    vi.unstubAllGlobals();
  });

  it('envia o access token no cabeçalho Authorization', () => {
    http.get('/api/v1/alunos').subscribe();
    const pedido = backend.expectOne('/api/v1/alunos');
    expect(pedido.request.headers.get('Authorization')).toBe('Bearer acesso-1');
    pedido.flush([]);
  });

  it('num 401 renova pelo cookie (sem refresh token no corpo) e repete o pedido com o token novo', async () => {
    const resposta = firstValueFrom(http.get('/api/v1/alunos'));

    backend.expectOne('/api/v1/alunos').flush({}, { status: 401, statusText: 'Unauthorized' });

    const refresh = backend.expectOne('/api/v1/auth/refresh');
    expect(refresh.request.body).toEqual({ refresh_token: null });
    refresh.flush({ access_token: 'acesso-2', refresh_token: 'nao-guardar' });

    const repetido = backend.expectOne('/api/v1/alunos');
    expect(repetido.request.headers.get('Authorization')).toBe('Bearer acesso-2');
    repetido.flush(['ok']);

    expect(await resposta).toEqual(['ok']);
    expect(localStorage.getItem('saas_access_token')).toBe('acesso-2');
    expect(localStorage.getItem('saas_refresh_token')).toBeNull();
  });

  it('migra uma sessão antiga: usa o refresh token do localStorage uma vez e apaga-o', async () => {
    localStorage.setItem('saas_refresh_token', 'antigo');
    const resposta = firstValueFrom(http.get('/api/v1/alunos'));
    backend.expectOne('/api/v1/alunos').flush({}, { status: 401, statusText: 'Unauthorized' });

    const refresh = backend.expectOne('/api/v1/auth/refresh');
    expect(refresh.request.body).toEqual({ refresh_token: 'antigo' });
    refresh.flush({ access_token: 'acesso-2', refresh_token: 'x' });
    backend.expectOne('/api/v1/alunos').flush([]);
    await resposta;

    expect(localStorage.getItem('saas_refresh_token')).toBeNull();
  });

  it('se a renovação falhar, termina a sessão (estado limpo + mensagem) e propaga o erro', async () => {
    const resposta = firstValueFrom(http.get('/api/v1/alunos')).catch(e => e);
    backend.expectOne('/api/v1/alunos').flush({}, { status: 401, statusText: 'Unauthorized' });
    backend.expectOne('/api/v1/auth/refresh').flush({ detail: 'expirada' }, { status: 401, statusText: 'Unauthorized' });

    const erro = await resposta;
    expect(erro.status).toBe(401);
    expect(await firstValueFrom(store.select(selectToken))).toBeNull();
    expect(await firstValueFrom(store.select(selectAuthError))).toContain('expirou');
  });

  it('vários 401 em paralelo provocam UM só refresh', async () => {
    const a = firstValueFrom(http.get('/api/v1/a'));
    const b = firstValueFrom(http.get('/api/v1/b'));
    backend.expectOne('/api/v1/a').flush({}, { status: 401, statusText: 'Unauthorized' });
    backend.expectOne('/api/v1/b').flush({}, { status: 401, statusText: 'Unauthorized' });

    backend.expectOne('/api/v1/auth/refresh').flush({ access_token: 'acesso-2' });
    backend.expectOne('/api/v1/a').flush('a');
    backend.expectOne('/api/v1/b').flush('b');
    expect([await a, await b]).toEqual(['a', 'b']);
  });

  it('um 401 no login (palavra-passe errada) não tenta renovar', async () => {
    const resposta = firstValueFrom(http.post('/api/v1/auth/login', {})).catch(e => e);
    backend.expectOne('/api/v1/auth/login').flush({}, { status: 401, statusText: 'Unauthorized' });
    expect((await resposta).status).toBe(401);
    backend.expectNone('/api/v1/auth/refresh');
  });
});
