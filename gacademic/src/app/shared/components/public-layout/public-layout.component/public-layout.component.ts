import { AsyncPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Store } from '@ngrx/store';
import { selectUsuario } from '../../../../store/auth/auth.selectors';

/**
 * Casca do site público (landing, funcionalidades, preços) — nav +
 * rodapé partilhados, mesmo padrão de dashboard-layout.component.ts
 * para a área autenticada. Não tem authGuard nenhum: é sempre visível,
 * mesmo com sessão iniciada (ver core/guards/publico.guard.ts para a
 * exceção — só a página inicial "/" redireciona quem já tem sessão).
 */
@Component({
  selector: 'app-public-layout.component',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, AsyncPipe],
  templateUrl: './public-layout.component.html',
  styleUrl: './public-layout.component.css',
})
export class PublicLayoutComponent {
  private store = inject(Store);
  usuario$ = this.store.select(selectUsuario);

  menuAberto = signal(false);

  alternarMenu() {
    this.menuAberto.update(v => !v);
  }

  fecharMenu() {
    this.menuAberto.set(false);
  }
}
