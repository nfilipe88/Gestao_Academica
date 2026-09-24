import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BehaviorSubject, of, Subject, throwError } from 'rxjs';
import { pollingContagem, ResultadoPolling, visibilidadeDoDocumento$ } from './polling-contagem';

describe('pollingContagem', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  const semJitter = { base: 60_000, maximo: 300_000, jitter: 0, aleatorio: () => 0.5 };

  it('pede logo e repete ao fim do intervalo', () => {
    const pedir = vi.fn(() => of(1));
    const sub = pollingContagem(pedir, { ...semJitter, visivel$: new BehaviorSubject(true) }).subscribe();
    expect(pedir).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(59_999);
    expect(pedir).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(1);
    expect(pedir).toHaveBeenCalledTimes(2);
    sub.unsubscribe();
  });

  it('não pede nada enquanto o separador está escondido e pede logo ao voltar a ficar visível', () => {
    const visivel$ = new BehaviorSubject(false);
    const pedir = vi.fn(() => of(1));
    const sub = pollingContagem(pedir, { ...semJitter, visivel$ }).subscribe();
    vi.advanceTimersByTime(10 * 60_000);
    expect(pedir).not.toHaveBeenCalled();

    visivel$.next(true);
    expect(pedir).toHaveBeenCalledTimes(1);

    visivel$.next(false);
    vi.advanceTimersByTime(10 * 60_000);
    expect(pedir).toHaveBeenCalledTimes(1);
    sub.unsubscribe();
  });

  it('recua depois de falhas (x2, x4… até ao máximo) e volta ao normal no primeiro sucesso', () => {
    let falha = true;
    const pedir = vi.fn(() => (falha ? throwError(() => new Error('down')) : of(7)));
    const resultados: ResultadoPolling<number>[] = [];
    const sub = pollingContagem(pedir, { ...semJitter, visivel$: new BehaviorSubject(true) }).subscribe(r => resultados.push(r));

    expect(pedir).toHaveBeenCalledTimes(1);            // t=0, falha 1
    vi.advanceTimersByTime(119_999); expect(pedir).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(1);       expect(pedir).toHaveBeenCalledTimes(2);   // +120 s
    vi.advanceTimersByTime(240_000); expect(pedir).toHaveBeenCalledTimes(3);   // +240 s
    vi.advanceTimersByTime(299_999); expect(pedir).toHaveBeenCalledTimes(3);
    vi.advanceTimersByTime(1);       expect(pedir).toHaveBeenCalledTimes(4);   // teto de 300 s

    falha = false;
    vi.advanceTimersByTime(300_000); expect(pedir).toHaveBeenCalledTimes(5);   // sucesso
    vi.advanceTimersByTime(60_000);  expect(pedir).toHaveBeenCalledTimes(6);   // de volta aos 60 s
    expect(resultados.filter(r => !r.ok).length).toBe(4);
    expect(resultados.at(-1)).toEqual({ ok: true, valor: 7 });
    sub.unsubscribe();
  });

  it('o jitter varia o intervalo em torno do base (±20%)', () => {
    const pedir = vi.fn(() => of(1));
    const sub = pollingContagem(pedir, { base: 60_000, jitter: 0.2, aleatorio: () => 0, visivel$: new BehaviorSubject(true) }).subscribe();
    vi.advanceTimersByTime(47_999); expect(pedir).toHaveBeenCalledTimes(1);   // 60 s × 0,8
    vi.advanceTimersByTime(1);      expect(pedir).toHaveBeenCalledTimes(2);
    sub.unsubscribe();
  });

  it('parar a subscrição pára os pedidos', () => {
    const pedir = vi.fn(() => of(1));
    pollingContagem(pedir, { ...semJitter, visivel$: new Subject<boolean>() }).subscribe().unsubscribe();
    vi.advanceTimersByTime(10 * 60_000);
    expect(pedir).not.toHaveBeenCalled();
  });
});

describe('visibilidadeDoDocumento$', () => {
  it('parte do estado atual e segue o evento visibilitychange', () => {
    let estado: 'visible' | 'hidden' = 'visible';
    const alvo = new EventTarget();
    Object.defineProperty(alvo, 'visibilityState', { get: () => estado });
    const doc = alvo as unknown as Document;
    const valores: boolean[] = [];
    visibilidadeDoDocumento$(doc).subscribe(v => valores.push(v));
    estado = 'hidden'; alvo.dispatchEvent(new Event('visibilitychange'));
    estado = 'visible'; alvo.dispatchEvent(new Event('visibilitychange'));
    expect(valores).toEqual([true, false, true]);
  });
});
