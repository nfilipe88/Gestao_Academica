import { AsyncPipe, CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { combineLatest, map, startWith } from 'rxjs';
import {
  atualizarLead, atualizarOportunidade, carregarFunil, carregarOportunidades, criarLead, moverOportunidade
} from '../../../store/crm/crm.actions';
import { OportunidadeCRM } from '../../../store/crm/crm.models';
import { selectCrmError, selectCrmMensagem, selectEtapas, selectOportunidades } from '../../../store/crm/crm.selector';
import { carregarCursos, carregarTurmas } from '../../../store/academico/academic.actions';
import { selectCursos, selectTurmas } from '../../../store/academico/academic.selector';

const ORIGENS = ['SITE', 'FACEBOOK', 'INDICACAO', 'PRESENCIAL', 'OUTRO'];

@Component({
  selector: 'app-crm.component',
  imports: [ReactiveFormsModule, FormsModule, CommonModule, AsyncPipe],
  templateUrl: './crm.component.html',
  styleUrl: './crm.component.css',
})
export class CrmComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private http = inject(HttpClient);

  private readonly rotulosDocumento: Record<string, string> = {
    BI: 'Cartão de Cidadão / BI', CERTIFICADO_HABILITACOES: 'Certificado de Habilitações', FOTO: 'Foto', OUTRO: 'Outro',
  };
  rotuloDocumento(tipo: string): string {
    return this.rotulosDocumento[tipo] ?? tipo;
  }

  // Abre a janela já (síncrono com o clique, para não ser bloqueada
  // como pop-up) e só preenche o conteúdo quando a data URI chega —
  // ver app/api/v1/crm.py::obter_documento_lead (pedida só ao abrir,
  // nunca embutida na listagem do quadro Kanban inteiro).
  onVerDocumento(leadId: string, documentoId: string) {
    const janela = window.open('', '_blank');
    this.http.get<{ url: string }>(`/api/v1/crm/leads/${leadId}/documentos/${documentoId}`).subscribe({
      next: (resp) => {
        janela?.document.write(`<iframe src="${resp.url}" style="border:0;position:fixed;inset:0;width:100%;height:100%"></iframe>`);
      },
      error: () => janela?.close(),
    });
  }

  erro$ = this.store.select(selectCrmError);
  mensagem$ = this.store.select(selectCrmMensagem);
  origens = ORIGENS;
  cursos$ = this.store.select(selectCursos);
  turmas$ = this.store.select(selectTurmas);

  // Filtro por origem do lead, curso de interesse e intervalo de
  // entrada — o quadro já carrega todas as oportunidades de uma vez,
  // por isso o filtro é só no cliente.
  filtroForm = this.fb.group({
    origem_lead: [''],
    curso_interesse_id: [''],
    data_entrada_inicio: [''],
    data_entrada_fim: ['']
  });

  // Cada etapa já com as suas oportunidades (para desenhar as colunas do Kanban).
  colunas$ = combineLatest([
    this.store.select(selectEtapas),
    this.store.select(selectOportunidades),
    this.filtroForm.valueChanges.pipe(startWith(this.filtroForm.value))
  ]).pipe(
    map(([etapas, oportunidades, filtro]) => {
      const filtradas = oportunidades.filter(o => {
        if (filtro.origem_lead && o.lead.origem_lead !== filtro.origem_lead) return false;
        if (filtro.curso_interesse_id && o.lead.curso_interesse_id !== filtro.curso_interesse_id) return false;
        if (filtro.data_entrada_inicio && o.lead.data_entrada < filtro.data_entrada_inicio) return false;
        if (filtro.data_entrada_fim && o.lead.data_entrada > filtro.data_entrada_fim) return false;
        return true;
      });
      return [...etapas]
        .sort((a, b) => a.ordem - b.ordem)
        .map(etapa => ({ etapa, cartoes: filtradas.filter(o => o.etapa_id === etapa.id) }));
    })
  );

  todasEtapas$ = this.store.select(selectEtapas);

  limparFiltro() {
    this.filtroForm.reset({ origem_lead: '', curso_interesse_id: '', data_entrada_inicio: '', data_entrada_fim: '' });
  }

  mostrarFormularioLead = false;
  nascimentoPorLead: Record<string, string> = {};

  // Turma pretendida + valor anual, editados por oportunidade — o que
  // falta à RN01 para, ao ganhar a oportunidade, gerar também Matrícula
  // e Contrato Financeiro automaticamente (ver onGuardarTurmaValor).
  turmaPorOportunidade: Record<string, string | undefined> = {};
  valorPorOportunidade: Record<string, number | null | undefined> = {};

  leadForm = this.fb.group({
    nome_responsavel: ['', Validators.required],
    email_contato: ['', Validators.email],
    telefone: [''],
    nome_aluno_candidato: ['', Validators.required],
    data_nascimento_candidato: [''],
    origem_lead: ['PRESENCIAL', Validators.required]
  });

  ngOnInit() {
    this.store.dispatch(carregarFunil());
    this.store.dispatch(carregarOportunidades());
    this.store.dispatch(carregarCursos());
    this.store.dispatch(carregarTurmas());
  }

  alternarFormularioLead() {
    this.mostrarFormularioLead = !this.mostrarFormularioLead;
    this.leadForm.reset({ origem_lead: 'PRESENCIAL' });
  }

  onSubmitLead() {
    if (this.leadForm.invalid) return;
    const { nome_responsavel, email_contato, telefone, nome_aluno_candidato, data_nascimento_candidato, origem_lead } = this.leadForm.value;
    this.store.dispatch(criarLead({
      nome_responsavel: nome_responsavel!,
      email_contato: email_contato || null,
      telefone: telefone || null,
      nome_aluno_candidato: nome_aluno_candidato!,
      data_nascimento_candidato: data_nascimento_candidato || null,
      origem_lead: origem_lead!
    }));
    this.mostrarFormularioLead = false;
  }

  onMover(oportunidadeId: string, novaEtapaId: string) {
    if (!novaEtapaId) return;
    this.store.dispatch(moverOportunidade({ oportunidade_id: oportunidadeId, nova_etapa_id: novaEtapaId }));
  }

  onGuardarNascimento(leadId: string) {
    const data = this.nascimentoPorLead[leadId];
    if (!data) return;
    this.store.dispatch(atualizarLead({ lead_id: leadId, data_nascimento_candidato: data }));
  }

  onGuardarTurmaValor(oportunidade: OportunidadeCRM) {
    const turmaId = this.turmaPorOportunidade[oportunidade.id] ?? oportunidade.turma_interesse_id ?? null;
    const valor = this.valorPorOportunidade[oportunidade.id] ?? oportunidade.valor_estimado_anual ?? null;
    if (!turmaId && valor == null) return;
    this.store.dispatch(atualizarOportunidade({
      oportunidade_id: oportunidade.id,
      turma_interesse_id: turmaId || null,
      valor_estimado_anual: valor
    }));
  }
}
