import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'app-registo.component',
  imports: [ReactiveFormsModule, CommonModule],
  templateUrl: './registo.component.html',
  styleUrl: './registo.component.css',
})
export class RegistoComponent {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private router = inject(Router);

  // Nenhum diálogo nativo (alert/confirm) — não é intercetável em
  // automação/testes e destoa do resto da UI, que nunca usa diálogos
  // nativos (mesmo padrão já seguido no resto da app, ex.:
  // features/admin/admin.component). Erro mostrado inline, sucesso
  // passado para o Login via queryParams (só o e-mail — nunca a
  // palavra-passe, que não deve viajar num URL).
  erro: string | null = null;

  registoForm = this.fb.group({
    nome_fantasia: ['', Validators.required],
    nif: ['', Validators.required],
    nome_gestor: ['', Validators.required],
    email_gestor: ['', [Validators.required, Validators.email]],
    palavra_passe: ['', [Validators.required, Validators.minLength(8)]]
  });

  onRegister() {
    if (this.registoForm.valid) {
      this.erro = null;
      this.http.post('/api/v1/auth/registo', this.registoForm.value)
        .subscribe({
          next: () => {
            this.router.navigate(['/login'], {
              queryParams: { registado: '1', email: this.registoForm.value.email_gestor }
            });
          },
          error: (err) => { this.erro = err.error?.detail || 'Não foi possível concluir o registo.'; }
        });
    }
  }
}
