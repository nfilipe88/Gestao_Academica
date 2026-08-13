import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { combineLatest, map } from 'rxjs';
import {
  atualizarLead, carregarFunil, carregarOportunidades, criarLead, moverOportunidade
} from '../../../store/crm/crm.actions';
import { selectCrmError, selectCrmMensagem, selectEtapas, selectOportunidades } from '../../../store/crm/crm.selector';

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

  // Cada etapa já com as suas oportunidades (para desenhar as colunas do Kanban).
  colunas$ = combineLatest([
    this.store.select(selectEtapas),
    this.store.select(selectOportunidades)
  ]).pipe(
    map(([etapas, oportunidades]) => [...etapas]
      .sort((a, b) => a.ordem - b.ordem)
      .map(etapa => ({ etapa, cartoes: oportunidades.filter(o => o.etapa_id === etapa.id) }))
    )
  );

  todasEtapas$ = this.store.select(selectEtapas);

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
