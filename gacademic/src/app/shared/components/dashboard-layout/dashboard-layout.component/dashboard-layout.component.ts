import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { logout } from '../../../../store/auth/auth.actions';
import { selectIsGestor, selectIsGestorOuSecretaria } from '../../../../store/auth/auth.selectors';
import { Store } from '@ngrx/store';

@Component({
  selector: 'app-dashboard-layout.component',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, AsyncPipe],
  templateUrl: './dashboard-layout.component.html',
  styleUrl: './dashboard-layout.component.css',
})
export class DashboardLayoutComponent {
  private store = inject(Store);
  isGestor$ = this.store.select(selectIsGestor);
  isGestorOuSecretaria$ = this.store.select(selectIsGestorOuSecretaria);

  sidebarColapsada = false;

  alternarSidebar() {
    this.sidebarColapsada = !this.sidebarColapsada;
  }

  onLogout() {
    // A navegação para /login acontece no AuthEffects (redirecionarAposLogout$).
    this.store.dispatch(logout());
  }
}
