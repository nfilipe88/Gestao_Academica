import { CurrencyPipe, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { SitePublico } from '../../../../shared/models/site-publico.models';

interface DocumentoAnexado {
  id: string;
  tipo: string;
  nome_original: string;
}

// Os 3 tipos de documento pedidos — ver TIPOS_DOCUMENTO_VALIDOS em
// back_end/app/cruds/crm.py (têm de ficar sincronizados).
const TIPOS_DOCUMENTO = [
  { chave: 'BI', rotulo: 'Cartão de Cidadão / BI' },
  { chave: 'CERTIFICADO_HABILITACOES', rotulo: 'Certificado de Habilitações' },
  { chave: 'FOTO', rotulo: 'Fotografia' },
] as const;

/**
 * Assistente de matrícula self-service (candidatura em 4 passos, com
 * upload de documentos) — página pública, sem autenticação. Ao
 * contrário do formulário rápido "Peça mais informações" (RN03,
 * shared/components/site-publico-lead-form), aqui cria-se logo o
 * Lead + Oportunidade no CRM com dados suficientes para a Secretaria
 * poder converter num único passo (mover o cartão para "Matriculado"
 * dispara a RN01 — ver app/cruds/crm.py::_converter_lead_em_aluno).
 *
 * O Lead é criado no fim do Passo 2 (assim que há curso escolhido),
 * não só no fim do assistente — os documentos do Passo 3 precisam de
 * um lead_id real para se anexarem a alguma coisa. Se o candidato
 * abandonar a meio, a candidatura parcial já fica visível à Secretaria
 * no CRM (comportamento aceitável, não um bug: nenhum dado é perdido).
 */
@Component({
  selector: 'app-matricula-wizard',
  imports: [ReactiveFormsModule, CurrencyPipe, DatePipe],
  templateUrl: './matricula-wizard.component.html',
  styleUrl: './matricula-wizard.component.css',
})
export class MatriculaWizardComponent implements OnInit {
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private fb = inject(FormBuilder);

  readonly tiposDocumento = TIPOS_DOCUMENTO;

  identificador = this.route.snapshot.paramMap.get('tenantId') ?? '';

  escola = signal<SitePublico | null>(null);
  aCarregar = signal(true);
  naoEncontrada = signal(false);

  passoAtual = signal(1);
  leadId = signal<string | null>(null);
  documentos = signal<DocumentoAnexado[]>([]);
  aEnviarTipo = signal<string | null>(null);
  concluido = signal(false);

  erro = signal<string | null>(null);
  aSubmeter = signal(false);

  form = this.fb.group({
    nome_responsavel: ['', Validators.required],
    email_contato: ['', Validators.email],
    telefone: [''],
    nome_aluno_candidato: ['', Validators.required],
    data_nascimento_candidato: ['', Validators.required],
    aceitou_regulamento: [false, Validators.requiredTrue],
    curso_interesse_id: [''],
  });

  ngOnInit() {
    if (!this.identificador) { this.naoEncontrada.set(true); this.aCarregar.set(false); return; }
    this.http.get<SitePublico>(`/api/v1/public/escola/${this.identificador}`).subscribe({
      next: (escola) => { this.escola.set(escola); this.aCarregar.set(false); },
      error: () => { this.naoEncontrada.set(true); this.aCarregar.set(false); },
    });
  }

  // Passo 1 — só validação client-side, nada é enviado ainda (o curso
  // do Passo 2 vai junto na mesma criação do Lead).
  onAvancarPasso1() {
    const c = this.form.controls;
    if (c.nome_responsavel.invalid || c.nome_aluno_candidato.invalid || c.data_nascimento_candidato.invalid
      || c.email_contato.invalid || c.aceitou_regulamento.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.passoAtual.set(2);
  }

  onVoltarPasso(destino: number) {
    this.erro.set(null);
    this.passoAtual.set(destino);
  }

  // Passo 2 — aqui sim cria-se o Lead + Oportunidade no CRM (RN03).
  onAvancarPasso2() {
    const tenantId = this.escola()?.tenant_id;
    if (!tenantId) return;
    this.erro.set(null);
    this.aSubmeter.set(true);
    const v = this.form.getRawValue();
    this.http.post<{ id: string }>(`/api/v1/public/${tenantId}/leads`, {
      nome_responsavel: v.nome_responsavel,
      email_contato: v.email_contato || null,
      telefone: v.telefone || null,
      nome_aluno_candidato: v.nome_aluno_candidato,
      data_nascimento_candidato: v.data_nascimento_candidato || null,
      curso_interesse_id: v.curso_interesse_id || null,
      aceitou_regulamento: v.aceitou_regulamento,
      origem_lead: 'SITE',
    }).subscribe({
      next: (resp) => {
        this.aSubmeter.set(false);
        this.leadId.set(resp.id);
        this.passoAtual.set(3);
      },
      error: (err) => {
        this.aSubmeter.set(false);
        const detail = err.error?.detail;
        this.erro.set(typeof detail === 'string' ? detail : 'Não foi possível enviar a candidatura. Tente novamente.');
      },
    });
  }

  // Passo 3 — documentos, cada um sobe assim que é escolhido.
  onSelecionarDocumento(evento: Event, tipo: string) {
    const ficheiro = (evento.target as HTMLInputElement).files?.[0];
    const tenantId = this.escola()?.tenant_id;
    const leadId = this.leadId();
    if (!ficheiro || !tenantId || !leadId) return;

    const dados = new FormData();
    dados.append('ficheiro', ficheiro);
    this.aEnviarTipo.set(tipo);
    this.erro.set(null);
    this.http.post<{ documentos: DocumentoAnexado[] }>(
      `/api/v1/public/${tenantId}/leads/${leadId}/documentos?tipo=${tipo}`, dados
    ).subscribe({
      next: (resp) => { this.aEnviarTipo.set(null); this.documentos.set(resp.documentos); },
      error: (err) => {
        this.aEnviarTipo.set(null);
        const detail = err.error?.detail;
        this.erro.set(typeof detail === 'string' ? detail : 'Não foi possível enviar o ficheiro. Tente novamente.');
      },
    });
    (evento.target as HTMLInputElement).value = '';
  }

  onRemoverDocumento(documentoId: string) {
    const tenantId = this.escola()?.tenant_id;
    const leadId = this.leadId();
    if (!tenantId || !leadId) return;
    this.http.delete<{ documentos: DocumentoAnexado[] }>(
      `/api/v1/public/${tenantId}/leads/${leadId}/documentos/${documentoId}`
    ).subscribe({ next: (resp) => this.documentos.set(resp.documentos) });
  }

  documentoDoTipo(tipo: string): DocumentoAnexado | undefined {
    return this.documentos().find(d => d.tipo === tipo);
  }

  nomeCurso(): string | null {
    const id = this.form.value.curso_interesse_id;
    if (!id) return null;
    return this.escola()?.cursos.find(c => c.id === id)?.nome ?? null;
  }

  onSubmeterFinal() {
    this.concluido.set(true);
  }
}
