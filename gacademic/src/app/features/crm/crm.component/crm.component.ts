import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { combineLatest, map, startWith } from 'rxjs';
import {
  atualizarLead, carregarFunil, carregarOportunidades, criarLead, moverOportunidade
} from '../../../store/crm/crm.actions';
import { selectCrmError, selectCrmMensagem, selectEtapas, selectOportunidades } from '../../../store/crm/crm.selector';
import { carregarCursos } from '../../../store/academico/academic.actions';
import { selectCursos } from '../../../store/academico/academic.selector';

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

  erro$ = this.store.select(selectCrmError);
  mensagem$ = this.store.select(selectCrmMensagem);
  origens = ORIGENS;
  cursos$ = this.store.select(selectCursos);

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
}
