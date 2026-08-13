import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

// Página pública de captação (RN03 do CRM) — pensada para ser
// incorporada (iframe/link) no site da própria escola. Sem authGuard,
// sem JWT: identifica a escola só pelo tenant_id na URL.
@Component({
  selector: 'app-captar-lead.component',
  imports: [ReactiveFormsModule, CommonModule],
  templateUrl: './captar-lead.component.html',
  styleUrl: './captar-lead.component.css',
})
export class CaptarLeadComponent {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);

  tenantId = this.route.snapshot.paramMap.get('tenantId') ?? '';

  enviado = false;
  erro: string | null = null;

  leadForm = this.fb.group({
    nome_responsavel: ['', Validators.required],
    email_contato: ['', Validators.email],
    telefone: [''],
    nome_aluno_candidato: ['', Validators.required],
    origem_lead: ['SITE']
  });

  onSubmit() {
    if (this.leadForm.invalid || !this.tenantId) return;
    this.erro = null;
    this.http.post(`/api/v1/public/${this.tenantId}/leads`, this.leadForm.value).subscribe({
      next: () => { this.enviado = true; },
      error: (err) => { this.erro = err.error?.detail || 'Não foi possível enviar o seu pedido. Tente novamente.'; }
    });
  }
}
