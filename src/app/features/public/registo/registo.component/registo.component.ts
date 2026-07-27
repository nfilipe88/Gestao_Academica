import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from 'express';

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

  registoForm = this.fb.group({
    nome_fantasia: ['', Validators.required],
    cnpj_nif: ['', Validators.required],
    nome_gestor: ['', Validators.required],
    email_gestor: ['', [Validators.required, Validators.email]],
    palavra_passe: ['', [Validators.required, Validators.minLength(8)]]
  });

  onRegister() {
    if (this.registoForm.valid) {
      this.http.post('/api/v1/auth/registo', this.registoForm.value)
        .subscribe({
          next: () => {
            alert('Instituição criada com sucesso! Redirecionando para o login.');
            this.router.navigate(['/login']);
          },
          error: (err) => alert(err.error?.detail || 'Erro ao efetuar registo.')
        });
    }
  }
}
