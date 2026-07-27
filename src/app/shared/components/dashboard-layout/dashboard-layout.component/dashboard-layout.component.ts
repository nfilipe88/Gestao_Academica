import { AsyncPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';
import { logout } from '../../../../store/auth/auth.actions';
import { selectIsGestor } from '../../../../store/auth/auth.selectors';
import { Store } from '@ngrx/store';

@Component({
  selector: 'app-dashboard-layout.component',
  imports: [RouterOutlet, RouterLink, AsyncPipe],
  templateUrl: './dashboard-layout.component.html',
  styleUrl: './dashboard-layout.component.css',
})
export class DashboardLayoutComponent {
  private store = inject(Store);
  isGestor$ = this.store.select(selectIsGestor);

  onLogout() {
    this.store.dispatch(logout());
    // O router irá reagir automaticamente à perda do token através do fluxo do sistema
    window.location.href = '/login';
  }
}
