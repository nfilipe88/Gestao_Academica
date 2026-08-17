import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

// Página pública (sem authGuard) — pede o link de redefinição por
// e-mail. A resposta da API é sempre a mesma mensagem genérica, exista
// ou não uma conta com este email (ver api/v1/auth.py::esqueci_senha),
// por isso o ecrã também não distingue os dois casos.
//
// Estado como signal, não propriedade simples: esta app não carrega
// zone.js (sem "polyfills" em angular.json) — sem zone.js, uma
// atribuição simples (`this.enviado = true`) dentro do callback
// assíncrono de subscribe() nunca dispara change detection (o
// coalescing de eventos do Angular zoneless só cobre a execução
// síncrona do próprio handler do evento, não o que acontece depois de
// a resposta HTTP chegar). Signals são o mecanismo que o CD zoneless
// de facto observa.
@Component({
  selector: 'app-esqueci-senha.component',
  imports: [ReactiveFormsModule, CommonModule],
  templateUrl: './esqueci-senha.component.html',
  styleUrl: './esqueci-senha.component.css',
})
export class EsqueciSenhaComponent {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);

  enviado = signal(false);
  aEnviar = signal(false);
  erro = signal<string | null>(null);

  form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
  });

  onSubmit() {
    if (this.form.invalid || this.aEnviar()) return;
    this.erro.set(null);
    this.aEnviar.set(true);
    this.http.post('/api/v1/auth/esqueci-senha', this.form.value).subscribe({
      next: () => { this.enviado.set(true); this.aEnviar.set(false); },
      error: (err) => {
        this.aEnviar.set(false);
        this.erro.set(err.error?.detail || 'Não foi possível processar o pedido. Tente novamente.');
      }
    });
  }
}
