import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { RecaptchaService } from '../../../../core/services/recaptcha.service';

// Página pública de captação (RN03 do CRM) — pensada para ser
// incorporada (iframe/link) no site da própria escola. Sem authGuard,
// sem JWT: identifica a escola só pelo tenant_id na URL.
//
// Estado como signal, não propriedade simples: esta app não carrega
// zone.js (sem "polyfills" em angular.json) — sem zone.js, uma
// atribuição simples (`this.enviado = true`) dentro do callback
// assíncrono de subscribe() nunca dispara change detection, e o ecrã
// ficava preso no formulário mesmo com o pedido a ter sido aceite
// (apanhado ao construir /esqueci-senha e /redefinir-senha, que
// copiaram este mesmo padrão).
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
  private recaptcha = inject(RecaptchaService);

  tenantId = this.route.snapshot.paramMap.get('tenantId') ?? '';

  enviado = signal(false);
  erro = signal<string | null>(null);

  leadForm = this.fb.group({
    nome_responsavel: ['', Validators.required],
    email_contato: ['', Validators.email],
    telefone: [''],
    nome_aluno_candidato: ['', Validators.required],
    origem_lead: ['SITE'],
    mensagem: ['']
  });

  async onSubmit() {
    if (this.leadForm.invalid || !this.tenantId) return;
    this.erro.set(null);
    const recaptcha_token = await this.recaptcha.obterToken('lead_publico');
    this.http.post(`/api/v1/public/${this.tenantId}/leads`, { ...this.leadForm.value, recaptcha_token }).subscribe({
      next: () => { this.enviado.set(true); },
      error: (err) => {
        const detail = err.error?.detail;
        this.erro.set(typeof detail === 'string' ? detail : 'Não foi possível enviar o seu pedido. Tente novamente.');
      }
    });
  }
}
