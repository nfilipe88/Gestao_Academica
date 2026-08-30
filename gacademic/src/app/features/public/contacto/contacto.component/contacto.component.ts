import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-contacto.component',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './contacto.component.html',
  styleUrl: './contacto.component.css',
})
export class ContactoComponent {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);

  enviado = signal(false);
  aEnviar = signal(false);
  erro = signal<string | null>(null);

  contactoForm = this.fb.group({
    nome: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    assunto: ['', Validators.required],
    mensagem: ['', Validators.required],
  });

  onSubmit() {
    if (this.contactoForm.invalid || this.aEnviar()) return;
    this.aEnviar.set(true);
    this.erro.set(null);
    this.http.post('/api/v1/public/tickets', this.contactoForm.getRawValue()).subscribe({
      next: () => { this.aEnviar.set(false); this.enviado.set(true); },
      error: (err) => { this.aEnviar.set(false); this.erro.set(err.error?.detail || 'Não foi possível enviar a sua mensagem. Tente novamente.'); }
    });
  }
}
