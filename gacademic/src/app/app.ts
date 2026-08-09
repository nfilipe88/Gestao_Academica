import { isPlatformBrowser } from '@angular/common';
import { Component, Inject, OnInit, PLATFORM_ID, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Store } from '@ngrx/store';
import { restoreAuth } from './store/auth/auth.actions';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  protected readonly title = signal('gacademic');

  // Utilizamos o Construtor para garantir a injeção segura no SSR
  constructor(
    private store: Store,
    @Inject(PLATFORM_ID) private platformId: Object
  ) { }

  ngOnInit() {
    if (isPlatformBrowser(this.platformId)) {
      const token = localStorage.getItem('saas_access_token');
      const userStr = localStorage.getItem('saas_user');
      const usuario = userStr ? JSON.parse(userStr) : null;

      this.store.dispatch(restoreAuth({ token, usuario }));
    }
  }
}
