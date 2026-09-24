import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { DOCUMENT } from '@angular/common';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideMockActions } from '@ngrx/effects/testing';
import { Observable, Subject } from 'rxjs';
import { Action } from '@ngrx/store';
import { NotificacoesEffects } from './notificacoes.effects';
import * as Acoes from './notificacoes.actions';
import { logout, sessaoExpirada } from '../auth/auth.actions';

describe('NotificacoesEffects — contagem periódica', () => {
  let acoes$: Subject<Action>;
  let backend: HttpTestingController;
  let efeitos: NotificacoesEffects;
  let emitidas: Action[];

  beforeEach(() => {
    vi.useFakeTimers();
    acoes$ = new Subject<Action>();
    TestBed.configureTestingModule({
      providers: [NotificacoesEffects, provideHttpClient(), provideHttpClientTesting(),
        provideMockActions(() => acoes$ as Observable<Action>), { provide: DOCUMENT, useValue: document }],
    });
    backend = TestBed.inject(HttpTestingController);
    efeitos = TestBed.inject(NotificacoesEffects);
    emitidas = [];
    efeitos.carregarContagem$.subscribe(a => emitidas.push(a));
  });
  afterEach(() => vi.useRealTimers());

  it('pede a contagem ao arrancar e guarda o total', () => {
    acoes$.next(Acoes.carregarContagem());
    backend.expectOne('/api/v1/notificacoes/contagem').flush({ total_nao_lidas: 3 });
    expect(emitidas).toEqual([Acoes.carregarContagemSucesso({ totalNaoLidas: 3 })]);
  });

  it('continua a perguntar de tempos a tempos', () => {
    acoes$.next(Acoes.carregarContagem());
    backend.expectOne('/api/v1/notificacoes/contagem').flush({ total_nao_lidas: 1 });
    vi.advanceTimersByTime(80_000);
    backend.expectOne('/api/v1/notificacoes/contagem').flush({ total_nao_lidas: 2 });
    expect(emitidas.at(-1)).toEqual(Acoes.carregarContagemSucesso({ totalNaoLidas: 2 }));
  });

  it.each([['logout', logout()], ['sessão expirada', sessaoExpirada()]])('pára de perguntar no %s', (_nome, acao) => {
    acoes$.next(Acoes.carregarContagem());
    backend.expectOne('/api/v1/notificacoes/contagem').flush({ total_nao_lidas: 1 });
    acoes$.next(acao);
    vi.advanceTimersByTime(10 * 60_000);
    backend.expectNone('/api/v1/notificacoes/contagem');
  });

  it('se o servidor falhar, emite o erro (sem rebentar o ciclo)', () => {
    acoes$.next(Acoes.carregarContagem());
    backend.expectOne('/api/v1/notificacoes/contagem').flush({ detail: 'Indisponível.' }, { status: 503, statusText: 'Service Unavailable' });
    expect((emitidas[0] as any).erro).toBe('Indisponível.');
  });
});
