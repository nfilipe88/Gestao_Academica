import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

/**
 * Ligação discreta "← Voltar ao início" para as páginas de ecrã inteiro sem
 * cabeçalho (login, registo, recuperar/redefinir palavra-passe, ativar conta…),
 * que antes não tinham forma de regressar à página inicial.
 */
@Component({
  selector: 'app-voltar-inicio',
  imports: [RouterLink],
  template: `
    <a [routerLink]="destino()"
      class="fixed top-4 left-4 z-30 inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800/70 focus-visible:outline-2 focus-visible:outline-blue-500 transition-colors">
      <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
      </svg>
      {{ rotulo() }}
    </a>
  `,
})
export class VoltarInicioComponent {
  destino = input<string | string[]>('/');
  rotulo = input('Voltar ao início');
}
