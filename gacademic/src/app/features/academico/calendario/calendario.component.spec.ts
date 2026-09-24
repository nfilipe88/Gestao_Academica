import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideStore, Store } from '@ngrx/store';
import { CalendarioComponent } from './calendario.component';
import { authReducer } from '../../../store/auth/auth.reducer';
import { loginSuccess } from '../../../store/auth/auth.actions';
import { GESTOR, instalarLocalStorageFalso } from '../../../testing/ajudas';

const ENTRADAS = [
  { id: 'e1', ano_letivo: 2026, tipo: 'EXAMES', nome: 'Exames do 1º trimestre', data_inicio: '2026-12-01', data_fim: '2026-12-12', observacoes: null, origem: 'CALENDARIO', estado: 'PROXIMO' },
  { id: null, ano_letivo: 2026, tipo: 'PERIODO_LETIVO', nome: '1º Trimestre', data_inicio: '2026-09-15', data_fim: '2026-11-30', observacoes: 'Definido no Diário de Classe', origem: 'DIARIO', estado: 'DECORRER' },
];

describe('CalendarioComponent', () => {
  let backend: HttpTestingController;
  let fixture: ComponentFixture<CalendarioComponent>;
  const raiz = () => fixture.nativeElement as HTMLElement;

  function abrir(perfil: object) {
    TestBed.inject(Store).dispatch(loginSuccess({ token: 't', usuario: perfil as any }));
    fixture = TestBed.createComponent(CalendarioComponent);
    fixture.detectChanges();
    backend.expectOne(r => r.url.startsWith('/api/v1/calendario?ano_letivo=')).flush(ENTRADAS);
    fixture.detectChanges();
  }

  beforeEach(() => {
    instalarLocalStorageFalso();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideStore({ auth: authReducer })],
    });
    backend = TestBed.inject(HttpTestingController);
  });
  afterEach(() => { backend.verify(); vi.unstubAllGlobals(); });

  it('lista os marcos com o tipo, o estado face a hoje e distingue os do Diário', () => {
    abrir(GESTOR);
    const texto = raiz().textContent ?? '';
    expect(texto).toContain('Exames do 1º trimestre');
    expect(texto).toContain('Próximo');
    expect(texto).toContain('A decorrer');
    expect(texto).toContain('Definido no Diário de Classe');
  });

  it('o Gestor vê o formulário e o botão Remover só nas entradas do calendário (não nas do Diário)', () => {
    abrir(GESTOR);
    expect(raiz().querySelector('form')).toBeTruthy();
    const remover = Array.from(raiz().querySelectorAll('button')).filter(b => b.textContent?.includes('Remover'));
    expect(remover.length).toBe(1);
  });

  it('quem não é Gestor só lê: sem formulário nem Remover', () => {
    abrir({ ...GESTOR, perfil_acesso: 'PROFESSOR' });
    expect(raiz().querySelector('form')).toBeNull();
    expect(Array.from(raiz().querySelectorAll('button')).some(b => b.textContent?.includes('Remover'))).toBe(false);
  });

  it('adicionar um marco envia o ano letivo e recarrega a lista', () => {
    abrir(GESTOR);
    const c = fixture.componentInstance;
    c.novo = { tipo: 'EXAMES_RECURSO', nome: 'Recurso de julho', data_inicio: '2027-07-01', data_fim: '2027-07-10', observacoes: '' };
    c.guardar();
    const post = backend.expectOne(r => r.method === 'POST' && r.url === '/api/v1/calendario');
    expect(post.request.body).toMatchObject({ tipo: 'EXAMES_RECURSO', nome: 'Recurso de julho', ano_letivo: c.ano, observacoes: null });
    post.flush({});
    backend.expectOne(r => r.method === 'GET').flush(ENTRADAS);
  });

  it('mostra o erro do servidor (ex.: datas trocadas) num alerta', () => {
    abrir(GESTOR);
    fixture.componentInstance.guardar();
    backend.expectOne(r => r.method === 'POST').flush({ detail: 'A data de início não pode ser depois da data de fim.' }, { status: 400, statusText: 'Bad Request' });
    fixture.detectChanges();
    expect(raiz().querySelector('[role="alert"]')?.textContent).toContain('data de início');
  });

  it('os campos do formulário têm etiqueta associada (acessibilidade)', () => {
    abrir(GESTOR);
    const etiquetas = Array.from(raiz().querySelectorAll('label[for]'));
    expect(etiquetas.length).toBeGreaterThanOrEqual(4);
    for (const e of etiquetas) expect(raiz().querySelector('#' + e.getAttribute('for'))).toBeTruthy();
  });
});
