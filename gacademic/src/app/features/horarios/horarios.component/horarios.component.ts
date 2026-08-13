import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { take } from 'rxjs';
import { carregarTurmas } from '../../../store/academico/academic.actions';
import { selectTurmas } from '../../../store/academico/academic.selector';
import { carregarAlocacoes } from '../../../store/professores/professores.actions';
import { selectAlocacoes } from '../../../store/professores/professores.selector';
import { selectIsGestorOuSecretaria } from '../../../store/auth/auth.selectors';
import {
  atualizarHorario, carregarGradeDaTurma, carregarMinhaGrade, criarHorario, removerHorario
} from '../../../store/horarios/horarios.actions';
import {
  selectGradeDaTurma, selectHorariosError, selectHorariosMensagem, selectMinhaGrade
} from '../../../store/horarios/horarios.selector';
import { HorarioAula } from '../../../store/horarios/horarios.models';

// 1=Segunda ... 7=Domingo (ISO 8601), igual ao back-end. Só mostramos
// Segunda-a-Sábado na grelha — a maioria das escolas não tem aulas ao
// Domingo, mas o modelo/validador aceitam o valor 7 na mesma.
const DIAS_DA_SEMANA = [
  { valor: 1, nome: 'Segunda' },
  { valor: 2, nome: 'Terça' },
  { valor: 3, nome: 'Quarta' },
  { valor: 4, nome: 'Quinta' },
  { valor: 5, nome: 'Sexta' },
  { valor: 6, nome: 'Sábado' },
];

@Component({
  selector: 'app-horarios.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe],
  templateUrl: './horarios.component.html',
  styleUrl: './horarios.component.css',
})
export class HorariosComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  turmas$ = this.store.select(selectTurmas);
  alocacoes$ = this.store.select(selectAlocacoes);
  gradeDaTurma$ = this.store.select(selectGradeDaTurma);
  minhaGrade$ = this.store.select(selectMinhaGrade);
  erro$ = this.store.select(selectHorariosError);
  mensagem$ = this.store.select(selectHorariosMensagem);
  podeGerir$ = this.store.select(selectIsGestorOuSecretaria);

  dias = DIAS_DA_SEMANA;

  turmaSelecionadaId = '';
  mostrarFormulario = false;
  horarioEmEdicaoId: string | null = null;

  form = this.fb.group({
    alocacao_id: ['', Validators.required],
    dia_semana: [1, Validators.required],
    hora_inicio: ['08:00', Validators.required],
    hora_fim: ['09:00', Validators.required],
    sala: [''],
  });

  ngOnInit() {
    this.store.dispatch(carregarTurmas());
    this.store.dispatch(carregarAlocacoes());
    this.store.dispatch(carregarMinhaGrade());
  }

  onSelecionarTurma(turmaId: string) {
    this.turmaSelecionadaId = turmaId;
    this.mostrarFormulario = false;
    this.horarioEmEdicaoId = null;
    if (turmaId) {
      this.store.dispatch(carregarGradeDaTurma({ turma_id: turmaId }));
    }
  }

  slotsDoDia(horarios: HorarioAula[] | null, dia: number): HorarioAula[] {
    if (!horarios) return [];
    return horarios.filter(h => h.dia_semana === dia).sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));
  }

  formatarHora(hora: string): string {
    return hora?.substring(0, 5) ?? '';
  }

  abrirFormularioNovo() {
    this.horarioEmEdicaoId = null;
    this.form.reset({ alocacao_id: '', dia_semana: 1, hora_inicio: '08:00', hora_fim: '09:00', sala: '' });
    this.mostrarFormulario = true;
  }

  editarSlot(horario: HorarioAula) {
    this.horarioEmEdicaoId = horario.id;
    this.form.reset({
      alocacao_id: horario.alocacao_id,
      dia_semana: horario.dia_semana,
      hora_inicio: this.formatarHora(horario.hora_inicio),
      hora_fim: this.formatarHora(horario.hora_fim),
      sala: horario.sala ?? '',
    });
    this.mostrarFormulario = true;
  }

  cancelarFormulario() {
    this.mostrarFormulario = false;
    this.horarioEmEdicaoId = null;
  }

  onSubmit() {
    if (this.form.invalid || !this.turmaSelecionadaId) return;
    const { alocacao_id, dia_semana, hora_inicio, hora_fim, sala } = this.form.value;
    const dados = {
      alocacao_id: alocacao_id!,
      dia_semana: Number(dia_semana),
      hora_inicio: `${hora_inicio}:00`,
      hora_fim: `${hora_fim}:00`,
      sala: sala || null,
    };

    if (this.horarioEmEdicaoId) {
      this.store.dispatch(atualizarHorario({ horario_id: this.horarioEmEdicaoId, dados, turma_id: this.turmaSelecionadaId }));
    } else {
      this.store.dispatch(criarHorario({ dados, turma_id: this.turmaSelecionadaId }));
    }
    this.mostrarFormulario = false;
    this.horarioEmEdicaoId = null;
  }

  removerSlot(horarioId: string) {
    if (!this.turmaSelecionadaId) return;
    this.store.dispatch(removerHorario({ horario_id: horarioId, turma_id: this.turmaSelecionadaId }));
  }

  alocacoesDaTurma(alocacoes: { id: string; turma_id: string; nome_disciplina: string }[] | null): { id: string; turma_id: string; nome_disciplina: string }[] {
    if (!alocacoes) return [];
    return alocacoes.filter(a => a.turma_id === this.turmaSelecionadaId);
  }
}
