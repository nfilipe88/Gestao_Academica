import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

// Página pública acedida a partir do link de e-mail — deliberadamente
// SEM guestGuard (ao contrário de /login e /esqueci-senha): quem clica
// no link pode ou não ter uma sessão antiga aberta noutro separador, e
// o link tem de funcionar em qualquer dos casos, porque quem autoriza
// a ação é o token na URL, não o estado de sessão do browser.
//
// Estado como signal, não propriedade simples: esta app não carrega
// zone.js (sem "polyfills" em angular.json) — sem zone.js, uma
// atribuição simples dentro do callback assíncrono de subscribe()
// nunca dispara change detection. Signals são o mecanismo que o CD
// zoneless de facto observa.
@Component({
  selector: 'app-redefinir-senha.component',
  imports: [ReactiveFormsModule, CommonModule],
  templateUrl: './redefinir-senha.component.html',
  styleUrl: './redefinir-senha.component.css',
})
export class RedefinirSenhaComponent {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  token = this.route.snapshot.queryParamMap.get('token') ?? '';

  concluido = signal(false);
  aEnviar = signal(false);
  erro = signal<string | null>(null);

  form = this.fb.group({
    nova_senha: ['', [Validators.required, Validators.minLength(8)]],
    confirmar_senha: ['', Validators.required],
  });

  get senhasDiferentes(): boolean {
    const { nova_senha, confirmar_senha } = this.form.value;
    return !!nova_senha && !!confirmar_senha && nova_senha !== confirmar_senha;
  }

  onSubmit() {
    if (this.form.invalid || this.senhasDiferentes || !this.token || this.aEnviar()) return;
    this.erro.set(null);
    this.aEnviar.set(true);
    this.http.post('/api/v1/auth/redefinir-senha', {
      token: this.token, nova_senha: this.form.value.nova_senha
    }).subscribe({
      next: () => {
        this.concluido.set(true);
        this.aEnviar.set(false);
        setTimeout(() => this.router.navigateByUrl('/login'), 3000);
      },
      error: (err) => {
        this.aEnviar.set(false);
        this.erro.set(err.error?.detail || 'Não foi possível redefinir a palavra-passe. Tente novamente.');
      }
    });
  }
}
