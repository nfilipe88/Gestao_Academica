import { AsyncPipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { IsActiveMatchOptions, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { logout } from '../../../../store/auth/auth.actions';
import { selectIsAlunoOuResponsavel, selectIsEquipaPlataforma, selectIsGestor, selectIsGestorOuSecretaria, selectIsSuperAdmin } from '../../../../store/auth/auth.selectors';
import { carregarConfiguracao } from '../../../../store/configuracoes/configuracoes.actions';
import { Store } from '@ngrx/store';
import { NotificacoesSinoComponent } from '../../notificacoes-sino/notificacoes-sino.component/notificacoes-sino.component';
import { NomesPerfisService } from '../../../../core/services/nomes-perfis.service';

@Component({
  selector: 'app-dashboard-layout.component',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, AsyncPipe, NotificacoesSinoComponent],
  templateUrl: './dashboard-layout.component.html',
  styleUrl: './dashboard-layout.component.css',
})
export class DashboardLayoutComponent implements OnInit {
  private store = inject(Store);
  private nomesPerfis = inject(NomesPerfisService);
  isGestor$ = this.store.select(selectIsGestor);
  isGestorOuSecretaria$ = this.store.select(selectIsGestorOuSecretaria);
  isAlunoOuResponsavel$ = this.store.select(selectIsAlunoOuResponsavel);
  isSuperAdmin$ = this.store.select(selectIsSuperAdmin);
  isEquipaPlataforma$ = this.store.select(selectIsEquipaPlataforma);

  sidebarColapsada = false;

  // Separadores do Portal (Dashboard/Horário/Boletim/...) viraram
  // entradas próprias do menu, todas apontando à mesma rota /portal
  // com um ?tab= diferente — precisa de comparar também os query
  // params (não só o caminho) para destacar a entrada certa, ao
  // contrário do resto do menu que só usa {exact:true}.
  readonly opcoesAtivasPortal: IsActiveMatchOptions = { paths: 'exact', queryParams: 'exact', fragment: 'ignored', matrixParams: 'ignored' };

  // Menu em telemóvel: gaveta escondida por omissão (< md), sem
  // relação com sidebarColapsada (que só faz sentido em ecrã largo —
  // "encolher para ícones"; numa gaveta de telemóvel não há esse meio-
  // termo, ou está aberta a toda a largura ou está fechada).
  sidebarMobileAberta = false;

  ngOnInit() {
    // Carregado aqui (shell comum a todo o utilizador autenticado,
    // staff e Portal) porque a moeda configurada é usada em toda a
    // plataforma para formatar valores monetários — incluindo os que
    // o Aluno/Responsável vê no Portal.
    this.store.dispatch(carregarConfiguracao());
    // Nomes dos perfis definidos pelo Super Admin (ex.: GESTOR → "Diretor
    // Geral") — usados pelo pipe nomePerfil em toda a app.
    this.nomesPerfis.carregar();
  }

  alternarSidebar() {
    this.sidebarColapsada = !this.sidebarColapsada;
  }

  alternarSidebarMobile() {
    this.sidebarMobileAberta = !this.sidebarMobileAberta;
  }

  fecharSidebarMobile() {
    this.sidebarMobileAberta = false;
  }

  onLogout() {
    // A navegação para /login acontece no AuthEffects (redirecionarAposLogout$).
    this.store.dispatch(logout());
  }
}
