import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

interface SitePublico {
  tenant_id: string;
  nome_fantasia: string;
  logotipo: string | null;
  missao: string | null;
  metodologia: string | null;
  telefone_contacto: string | null;
  email_contacto: string | null;
  morada: string | null;
  cidade: string | null;
  cursos: string[];
  fotos: string[];
}

/**
 * Página pública de apresentação de UMA escola cliente (marketing/
 * angariação de alunos) — distinta do site público da PLATAFORMA
 * (features/public/landing/...): aqui é a escola que se apresenta a
 * famílias, com a marca dela (logótipo, nome), não a nossa. Por isso
 * fica FORA de PublicLayoutComponent (sem o nav/rodapé "SaaS
 * Académico") — mesmo raciocínio de captar-lead.component, que também
 * é uma página standalone por pertencer à escola, não à plataforma.
 */
@Component({
  selector: 'app-escola.component',
  imports: [ReactiveFormsModule],
  templateUrl: './escola.component.html',
  styleUrl: './escola.component.css',
})
export class EscolaComponent implements OnInit {
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private fb = inject(FormBuilder);

  tenantId = this.route.snapshot.paramMap.get('tenantId') ?? '';

  escola = signal<SitePublico | null>(null);
  aCarregar = signal(true);
  naoEncontrada = signal(false);

  leadEnviado = signal(false);
  erroLead = signal<string | null>(null);
  leadForm = this.fb.group({
    nome_responsavel: ['', Validators.required],
    email_contato: ['', Validators.email],
    telefone: [''],
    nome_aluno_candidato: ['', Validators.required],
    origem_lead: ['SITE'],
  });

  ngOnInit() {
    if (!this.tenantId) { this.naoEncontrada.set(true); this.aCarregar.set(false); return; }
    this.http.get<SitePublico>(`/api/v1/public/escola/${this.tenantId}`).subscribe({
      next: (escola) => { this.escola.set(escola); this.aCarregar.set(false); },
      error: () => { this.naoEncontrada.set(true); this.aCarregar.set(false); },
    });
  }

  onSubmitLead() {
    if (this.leadForm.invalid || !this.tenantId) return;
    this.erroLead.set(null);
    this.http.post(`/api/v1/public/${this.tenantId}/leads`, this.leadForm.value).subscribe({
      next: () => { this.leadEnviado.set(true); },
      error: (err) => { this.erroLead.set(err.error?.detail || 'Não foi possível enviar o seu pedido. Tente novamente.'); }
    });
  }
}
