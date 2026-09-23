import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideStore, Store } from '@ngrx/store';
import { firstValueFrom } from 'rxjs';
import { vi } from 'vitest';
import { App } from './app';
import { authReducer } from './store/auth/auth.reducer';
import { selectToken, selectUsuario } from './store/auth/auth.selectors';

// O scaffold original do Angular CLI (imports: [App], sem mais nada, à
// procura de um <h1>"Hello, gacademic"</h1> que nunca existiu neste
// projeto) nunca tinha sido atualizado — App injeta Store e Router
// (ver app.ts), por isso qualquer teste real precisa dos providers
// mínimos abaixo (NG0201 sem eles). Só o slice "auth" do store é
// fornecido: é o único que App lê/escreve diretamente (restoreAuth, ao
// arrancar, a partir do localStorage) — os restantes ~25 reducers/
// effects de app.config.ts pertencem às features, não a este teste.
//
// localStorage é substituído por um duplo em memória (via
// vi.stubGlobal), em vez de usar o global real do ambiente de teste:
// o Node 22+ expõe o seu próprio `localStorage` experimental, que pode
// sobrepor-se ao do jsdom consoante a ordem de inicialização — um
// duplo próprio evita depender de qual dos dois "ganhou" nesta versão.
function _criarLocalStorageFalso(): Storage {
  const dados = new Map<string, string>();
  return {
    getItem: (chave: string) => dados.get(chave) ?? null,
    setItem: (chave: string, valor: string) => { dados.set(chave, valor); },
    removeItem: (chave: string) => { dados.delete(chave); },
    clear: () => { dados.clear(); },
    key: (indice: number) => Array.from(dados.keys())[indice] ?? null,
    get length() { return dados.size; },
  } as Storage;
}

describe('App', () => {
  beforeEach(async () => {
    vi.stubGlobal('localStorage', _criarLocalStorageFalso());
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        provideStore({ auth: authReducer }),
      ],
    }).compileComponents();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('cria a aplicação sem sessão guardada', () => {
    const fixture = TestBed.createComponent(App);
    expect(() => fixture.detectChanges()).not.toThrow();
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('restaura a sessão a partir do localStorage ao arrancar', async () => {
    localStorage.setItem('saas_access_token', 'token-de-teste');
    localStorage.setItem('saas_user', JSON.stringify({ id: 'u1', perfil_acesso: 'GESTOR' }));

    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const store = TestBed.inject(Store);
    expect(await firstValueFrom(store.select(selectToken))).toBe('token-de-teste');
    expect((await firstValueFrom(store.select(selectUsuario)))?.perfil_acesso).toBe('GESTOR');
  });
});
