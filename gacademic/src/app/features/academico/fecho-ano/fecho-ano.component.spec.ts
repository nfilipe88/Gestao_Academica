import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideStore, Store } from '@ngrx/store';
import { FechoAnoComponent } from './fecho-ano.component';
import { authReducer } from '../../../store/auth/auth.reducer';
import { loginSuccess } from '../../../store/auth/auth.actions';
import { GESTOR, instalarLocalStorageFalso } from '../../../testing/ajudas';

const PERIODOS = [{ id: 'p1', nome: '1º Trimestre', aberto: true }, { id: 'p2', nome: '2º Trimestre', aberto: false }];

function previa(extra: object = {}) {
  return {
    ano_letivo: 2026, nota_minima_aprovacao: 10, max_disciplinas_reprovadas: 0, limite_faltas_percentagem: 25,
    periodos_abertos: [], pode_fechar: true, ja_fechados: 0,
    resumo: { total: 3, aprovado: 1, reprovado: 1, reprovado_faltas: 0, incompleto: 1 },
    alunos: [
      { nome_completo: 'Ana Silva', turma: '10ª A', resultado: 'APROVADO', resultado_atual: null, disciplinas: [{ nome: 'Mat', m_final: 15, completa: true, aprovada: true }], em_falta: [], faltas_percentagem: 0 },
      { nome_completo: 'Bruno Costa', turma: '10ª A', resultado: 'REPROVADO', resultado_atual: null, disciplinas: [], em_falta: [], faltas_percentagem: 0 },
      { nome_completo: 'Eva Lopes', turma: '10ª A', resultado: 'INCOMPLETO', resultado_atual: null, disciplinas: [], em_falta: ['Matemática'], faltas_percentagem: 0 },
    ],
    ...extra,
  };
}

describe('FechoAnoComponent', () => {
  let backend: HttpTestingController;
  let fixture: ComponentFixture<FechoAnoComponent>;
  const texto = () => (fixture.nativeElement as HTMLElement).textContent ?? '';
  const botao = (rotulo: string) =>
    Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find(b => b.textContent?.includes(rotulo)) as HTMLButtonElement | undefined;

  async function abrir(perfil = GESTOR) {
    TestBed.inject(Store).dispatch(loginSuccess({ token: 't', usuario: perfil }));
    fixture = TestBed.createComponent(FechoAnoComponent);
    fixture.detectChanges();
    backend.expectOne('/api/v1/diario/periodos').flush(PERIODOS);
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

  it('lista os trimestres com o estado e só o Gestor vê "Trancar" nos abertos', async () => {
    await abrir();
    expect(texto()).toContain('1º Trimestre');
    expect(texto()).toContain('Aberto');
    expect(texto()).toContain('Trancado');
    expect(botao('Trancar trimestre')).toBeTruthy();
  });

  it('a Secretaria vê as pendências mas não pode trancar', async () => {
    await abrir({ ...GESTOR, perfil_acesso: 'SECRETARIA' });
    expect(botao('Ver pendências')).toBeTruthy();
    expect(botao('Trancar trimestre')).toBeUndefined();
  });

  it('mostra as pendências do trimestre com turma, disciplina, professor e alunos', async () => {
    await abrir();
    botao('Ver pendências')!.click();
    backend.expectOne('/api/v1/fecho/periodos/p1/pendencias').flush({
      periodo: '1º Trimestre', ano_letivo: 2026, total_alunos_sem_nota: 2,
      pendencias: [{ turma: '10ª A', disciplina: 'Matemática', professor: 'Prof. Rui', total_alunos: 6, sem_nota: 2, alunos_sem_nota: ['Bruno', 'Carla'] }],
    });
    fixture.detectChanges();
    expect(texto()).toContain('2 nota(s) em falta');
    expect(texto()).toContain('Prof. Rui');
    expect(texto()).toContain('Bruno, Carla');
  });

  it('mostra a prévia do ano com os resultados por aluno', async () => {
    await abrir();
    botao('Ver prévia')!.click();
    backend.expectOne(r => r.url.endsWith('/previa')).flush(previa());
    fixture.detectChanges();
    expect(texto()).toContain('Ana Silva');
    expect(texto()).toContain('Aprovado');
    expect(texto()).toContain('Reprovado');
    expect(texto()).toContain('Notas em falta: Matemática');
  });

  it('não deixa fechar o ano enquanto houver períodos abertos', async () => {
    await abrir();
    botao('Ver prévia')!.click();
    backend.expectOne(r => r.url.endsWith('/previa')).flush(previa({ pode_fechar: false, periodos_abertos: ['1º Trimestre'] }));
    fixture.detectChanges();
    expect(botao('Fechar o ano')!.disabled).toBe(true);
    expect(texto()).toContain('Tranque primeiro: 1º Trimestre');
  });

  it('fechar o ano pede confirmação e só então chama a API', async () => {
    await abrir();
    botao('Ver prévia')!.click();
    backend.expectOne(r => r.url.endsWith('/previa')).flush(previa());
    fixture.detectChanges();

    botao('Fechar o ano')!.click();
    fixture.detectChanges();
    backend.expectNone(r => r.method === 'POST');
    expect(texto()).toContain('Confirmar?');

    botao('Sim, fechar')!.click();
    const fecho = backend.expectOne(r => r.method === 'POST' && /\/fecho\/ano\/\d+$/.test(r.url));
    fecho.flush({ fechados: 2, incompletos: [{ aluno: 'Eva Lopes' }], completo: false });
    backend.expectOne(r => r.url.endsWith('/previa')).flush(previa({ ja_fechados: 2 }));
    fixture.detectChanges();
    expect(texto()).toContain('2 resultado(s) gravado(s)');
    expect(texto()).toContain('1 aluno(s) ficaram por fechar');
  });

  it('mostra o erro devolvido pelo servidor num alerta acessível', async () => {
    await abrir();
    botao('Ver prévia')!.click();
    backend.expectOne(r => r.url.endsWith('/previa')).flush({ detail: 'Sem permissão.' }, { status: 403, statusText: 'Forbidden' });
    fixture.detectChanges();
    const alerta = (fixture.nativeElement as HTMLElement).querySelector('[role="alert"]');
    expect(alerta?.textContent).toContain('Sem permissão.');
  });
});
