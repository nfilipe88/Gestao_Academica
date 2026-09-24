import { VoltarInicioComponent } from '../../../../shared/components/voltar-inicio/voltar-inicio.component';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

// Página pública acedida a partir do link de e-mail de ativação —
// deliberadamente SEM guestGuard (mesmo motivo de
// redefinir-senha.component: quem clica no link pode ou não ter uma
// sessão antiga aberta noutro separador, e o link tem de funcionar em
// qualquer dos casos, porque quem autoriza a ação é o token na URL, não
// o estado de sessão do browser).
//
// Ao contrário da redefinição de senha, não há formulário nenhum a
// preencher aqui — o único dado necessário (o token) já vem na URL, por
// isso a ativação dispara automaticamente ao carregar a página.
//
// Estado como signal, não propriedade simples: esta app não carrega
// zone.js — sem zone.js, uma atribuição simples dentro do callback
// assíncrono de subscribe() nunca dispara change detection. Signals são
// o mecanismo que o CD zoneless de facto observa.
@Component({
  selector: 'app-ativar-conta.component',
  imports: [CommonModule, VoltarInicioComponent],
  templateUrl: './ativar-conta.component.html',
  styleUrl: './ativar-conta.component.css',
})
export class AtivarContaComponent implements OnInit {
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  token = this.route.snapshot.queryParamMap.get('token') ?? '';

  aAtivar = signal(false);
  concluido = signal(false);
  erro = signal<string | null>(null);

  ngOnInit() {
    if (!this.token) return;
    this.aAtivar.set(true);
    this.http.post('/api/v1/auth/ativar-conta', { token: this.token }).subscribe({
      next: () => {
        this.aAtivar.set(false);
        this.concluido.set(true);
        this.router.navigate(['/login'], { queryParams: { ativado: '1' } });
      },
      error: (err) => {
        this.aAtivar.set(false);
        this.erro.set(err.error?.detail || 'Não foi possível ativar a conta. Tente novamente.');
      }
    });
  }
}
