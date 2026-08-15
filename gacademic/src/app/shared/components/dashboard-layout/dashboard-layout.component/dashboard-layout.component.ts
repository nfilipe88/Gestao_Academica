import { AsyncPipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { logout } from '../../../../store/auth/auth.actions';
import { selectIsAlunoOuResponsavel, selectIsGestor, selectIsGestorOuSecretaria, selectIsSuperAdmin } from '../../../../store/auth/auth.selectors';
import { carregarConfiguracao } from '../../../../store/configuracoes/configuracoes.actions';
import { Store } from '@ngrx/store';
import { NotificacoesSinoComponent } from '../../notificacoes-sino/notificacoes-sino.component/notificacoes-sino.component';

@Component({
  selector: 'app-dashboard-layout.component',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, AsyncPipe, NotificacoesSinoComponent],
  templateUrl: './dashboard-layout.component.html',
  styleUrl: './dashboard-layout.component.css',
})
export class DashboardLayoutComponent implements OnInit {
  private store = inject(Store);
  isGestor$ = this.store.select(selectIsGestor);
  isGestorOuSecretaria$ = this.store.select(selectIsGestorOuSecretaria);
  isAlunoOuResponsavel$ = this.store.select(selectIsAlunoOuResponsavel);
  isSuperAdmin$ = this.store.select(selectIsSuperAdmin);

  sidebarColapsada = false;

  ngOnInit() {
    // Carregado aqui (shell comum a todo o utilizador autenticado,
    // staff e Portal) porque a moeda configurada é usada em toda a
    // plataforma para formatar valores monetários — incluindo os que
    // o Aluno/Responsável vê no Portal.
    this.store.dispatch(carregarConfiguracao());
  }

  alternarSidebar() {
    this.sidebarColapsada = !this.sidebarColapsada;
  }

  onLogout() {
    // A navegação para /login acontece no AuthEffects (redirecionarAposLogout$).
    this.store.dispatch(logout());
  }
}
