import { isPlatformBrowser } from '@angular/common';
import { Component, Inject, OnInit, PLATFORM_ID, signal } from '@angular/core';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { Store } from '@ngrx/store';
import { restoreAuth } from './store/auth/auth.actions';
import { SuporteVirtualWidgetComponent } from './shared/components/suporte-virtual-widget/suporte-virtual-widget.component/suporte-virtual-widget.component';

// Rotas com a marca da própria escola, não da plataforma — a página
// pública de uma escola (features/public/escola) e o widget de
// captação de lead pensado para ser embutido no site da escola
// (features/public/captar-lead). Mostrar aqui o "Suporte Virtual" da
// PLATAFORMA ("tira dúvidas sobre módulos, preços...") não faz
// sentido nenhum para quem está a ver a página de uma escola — e
// contradiz o próprio propósito destas páginas ficarem fora do
// PublicLayoutComponent (ver escola.component.ts).
const PREFIXOS_SEM_MARCA_DA_PLATAFORMA = ['/escola/', '/captar/'];

@Component({
  selector: 'app-root',
  // Widget flutuante montado uma única vez aqui na raiz — fica visível
  // tanto no site público como dentro da app autenticada, sem precisar
  // de o duplicar em public-layout e em dashboard-layout (exceto nas
  // rotas com a marca da própria escola — ver mostrarWidgetSuporte).
  imports: [RouterOutlet, SuporteVirtualWidgetComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  protected readonly title = signal('gacademic');
  protected readonly mostrarWidgetSuporte = signal(true);

  // Utilizamos o Construtor para garantir a injeção segura no SSR
  constructor(
    private store: Store,
    private router: Router,
    @Inject(PLATFORM_ID) private platformId: Object
  ) { }

  ngOnInit() {
    if (isPlatformBrowser(this.platformId)) {
      const token = localStorage.getItem('saas_access_token');
      const userStr = localStorage.getItem('saas_user');
      const usuario = userStr ? JSON.parse(userStr) : null;

      this.store.dispatch(restoreAuth({ token, usuario }));
    }

    this._atualizarVisibilidadeWidget(this.router.url);
    this.router.events.pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe((e) => this._atualizarVisibilidadeWidget(e.urlAfterRedirects));
  }

  private _atualizarVisibilidadeWidget(url: string) {
    this.mostrarWidgetSuporte.set(!PREFIXOS_SEM_MARCA_DA_PLATAFORMA.some(p => url.startsWith(p)));
  }
}
