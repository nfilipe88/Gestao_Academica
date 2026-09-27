import { describe, expect, it } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { ToastHostComponent } from './toast-host.component';
import { ToastService } from '../../../core/services/toast.service';

describe('ToastHostComponent', () => {
  function criar() {
    TestBed.configureTestingModule({});
    const fixture = TestBed.createComponent(ToastHostComponent);
    const toast = TestBed.inject(ToastService);
    return { fixture, toast, raiz: () => fixture.nativeElement as HTMLElement };
  }

  it('nada visível sem toasts', () => {
    const { fixture, raiz } = criar();
    fixture.detectChanges();
    expect(raiz().querySelector('[role="alert"]')).toBeNull();
  });

  it('mostra um erro como role=alert e fecha ao clicar', () => {
    const { fixture, toast, raiz } = criar();
    toast.mostrarErro('Ocorreu um erro inesperado no servidor.');
    fixture.detectChanges();

    const alerta = raiz().querySelector('[role="alert"]');
    expect(alerta?.textContent).toContain('Ocorreu um erro inesperado no servidor.');

    (raiz().querySelector('button[aria-label="Fechar aviso"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(raiz().querySelector('[role="alert"]')).toBeNull();
  });
});
