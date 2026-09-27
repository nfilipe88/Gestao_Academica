import { Component, inject } from '@angular/core';
import { ToastService } from '../../../core/services/toast.service';

/**
 * Montado uma única vez na raiz (ver app.html), tal como o sino de
 * notificações — mas este é global a TODA a app (site público, login e
 * área autenticada), porque um erro inesperado pode acontecer em qualquer
 * uma. Ver ToastService para o porquê de existir.
 */
@Component({
  selector: 'app-toast-host',
  template: `
    <div class="fixed bottom-4 right-4 z-100 flex flex-col gap-2 w-full max-w-sm pointer-events-none" aria-live="assertive">
      @for (t of toast.toasts(); track t.id) {
        <div role="alert"
          class="pointer-events-auto flex items-start gap-3 rounded-lg bg-rose-600 px-4 py-3 text-sm text-white shadow-lg shadow-rose-900/20">
          <span class="flex-1">{{ t.mensagem }}</span>
          <button type="button" (click)="toast.remover(t.id)" aria-label="Fechar aviso"
            class="shrink-0 text-white/80 hover:text-white cursor-pointer leading-none">✕</button>
        </div>
      }
    </div>
  `,
})
export class ToastHostComponent {
  protected toast = inject(ToastService);
}
