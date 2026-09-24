import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AsyncPipe } from '@angular/common';
import { Store } from '@ngrx/store';
import { filter, take } from 'rxjs';
import { logout } from '../../../store/auth/auth.actions';
import { aceitarTermos } from '../../../store/configuracoes/configuracoes.actions';
import { selectConfiguracao, selectConfiguracoesError } from '../../../store/configuracoes/configuracoes.selector';

/**
 * Primeiro acesso do Gestor de uma escola criada pelo Super Admin: tem de
 * aceitar a Política de Privacidade e os Termos antes de usar a plataforma
 * (ver core/guards/termos.guard.ts). A escola é a responsável pelos dados
 * dos seus alunos, por isso a aceitação é dela, não do Super Admin.
 */
@Component({
  selector: 'app-aceitar-termos',
  imports: [FormsModule, RouterLink, AsyncPipe],
  template: `
    <main class="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <section class="max-w-lg w-full rounded-xl border border-slate-800 bg-slate-900 p-8 text-slate-300 text-sm leading-relaxed">
        <h1 class="text-2xl font-bold text-white mb-2">Antes de começar</h1>
        <p>A sua escola foi criada pela equipa da plataforma. Como responsável pelos dados dos alunos, encarregados de
          educação e professores, tem de aceitar a Política de Privacidade e os Termos em nome da escola.</p>

        <label class="mt-5 flex items-start gap-2">
          <input type="checkbox" [(ngModel)]="aceite" class="mt-1" />
          <span>Li e aceito, em nome da escola, a
            <a routerLink="/privacidade" target="_blank" class="text-blue-400 underline">Política de Privacidade e os Termos</a>.</span>
        </label>

        @if (erro$ | async; as erro) {
          <p class="mt-3 text-red-400">{{ erro }}</p>
        }

        <button type="button" (click)="confirmar()" [disabled]="!aceite || aEnviar"
          class="mt-6 w-full rounded-lg bg-blue-600 px-4 py-2 font-medium text-white disabled:opacity-50">
          Aceitar e continuar
        </button>
        <button type="button" (click)="sair()" class="mt-3 w-full text-xs text-slate-400 hover:text-white cursor-pointer">Terminar sessão</button>
      </section>
    </main>
  `,
})
export class AceitarTermosComponent {
  private store = inject(Store);
  private router = inject(Router);

  aceite = false;
  aEnviar = false;
  erro$ = this.store.select(selectConfiguracoesError);

  sair() { this.store.dispatch(logout()); }

  confirmar() {
    this.aEnviar = true;
    this.store.dispatch(aceitarTermos());
    this.store.select(selectConfiguracao).pipe(filter(c => !!c.termos_aceites_em), take(1))
      .subscribe(() => this.router.navigateByUrl('/'));
    this.erro$.pipe(filter(e => !!e), take(1)).subscribe(() => (this.aEnviar = false));
  }
}
