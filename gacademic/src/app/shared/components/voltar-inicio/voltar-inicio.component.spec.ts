import { describe, expect, it } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { VoltarInicioComponent } from './voltar-inicio.component';

describe('VoltarInicioComponent', () => {
  function criar(entradas: Record<string, unknown> = {}) {
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    const fixture = TestBed.createComponent(VoltarInicioComponent);
    for (const [k, v] of Object.entries(entradas)) fixture.componentRef.setInput(k, v);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('por omissão leva à página inicial com o texto "Voltar ao início"', () => {
    const a = criar().querySelector('a')!;
    expect(a.getAttribute('href')).toBe('/');
    expect(a.textContent).toContain('Voltar ao início');
  });

  it('aceita outro destino e outro texto', () => {
    const a = criar({ destino: '/escola/abc', rotulo: 'Voltar à escola' }).querySelector('a')!;
    expect(a.getAttribute('href')).toBe('/escola/abc');
    expect(a.textContent).toContain('Voltar à escola');
  });

  it('o ícone é decorativo (escondido dos leitores de ecrã)', () => {
    expect(criar().querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
  });
});
