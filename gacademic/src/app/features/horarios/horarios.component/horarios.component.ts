import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { Subscription, take } from 'rxjs';
import { carregarTurmas } from '../../../store/academico/academic.actions';
import { selectTurmas } from '../../../store/academico/academic.selector';
import { carregarAlocacoes } from '../../../store/professores/professores.actions';
import { selectAlocacoes } from '../../../store/professores/professores.selector';
import { selectIsGestorOuSecretaria } from '../../../store/auth/auth.selectors';
import {
  atualizarHorario, carregarAulasPorLancar, carregarGradeDaTurma, carregarGradeDoProfessor,
  carregarMinhaGrade, criarHorario, limparGradeDoProfessor, removerHorario
} from '../../../store/horarios/horarios.actions';
import {
  selectAulasPorLancar, selectGradeDaTurma, selectGradeDoProfessor, selectHorariosError,
  selectHorariosMensagem, selectMinhaGrade
} from '../../../store/horarios/horarios.selector';
import { HorarioAula } from '../../../store/horarios/horarios.models';
import { agendarAvaliacaoGeral, carregarAvaliacoesAgendadas, carregarPeriodos } from '../../../store/diario/diario.actions';
import { selectAvaliacoesAgendadas, selectDiarioError, selectDiarioMensagem, selectPeriodos } from '../../../store/diario/diario.selector';
import { carregarTiposAvaliacao } from '../../../store/configuracoes/configuracoes.actions';
import { selectTiposAvaliacaoAtivos } from '../../../store/configuracoes/configuracoes.selector';

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
export class HorariosComponent implements OnInit, OnDestroy {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private subscricoes = new Subscription();

  turmas$ = this.store.select(selectTurmas);
  alocacoes$ = this.store.select(selectAlocacoes);
  gradeDaTurma$ = this.store.select(selectGradeDaTurma);
  minhaGrade$ = this.store.select(selectMinhaGrade);
  gradeDoProfessor$ = this.store.select(selectGradeDoProfessor);
  aulasPorLancar$ = this.store.select(selectAulasPorLancar);
  erro$ = this.store.select(selectHorariosError);
  mensagem$ = this.store.select(selectHorariosMensagem);
  podeGerir$ = this.store.select(selectIsGestorOuSecretaria);

  // Avaliações/exames com hora marcada (ver Diário) — painel visível a
  // todo o staff; o back-end já filtra para o Professor só ver as suas
  // próprias alocações (RN01), por isso não é preciso repetir o filtro aqui.
  avaliacoesAgendadas$ = this.store.select(selectAvaliacoesAgendadas);
  periodos$ = this.store.select(selectPeriodos);
  tiposComAgendamento$ = this.store.select(selectTiposAvaliacaoAtivos);
  avaliacaoErro$ = this.store.select(selectDiarioError);
  avaliacaoMensagem$ = this.store.select(selectDiarioMensagem);

  dias = DIAS_DA_SEMANA;

  turmaSelecionadaId = '';
  mostrarFormulario = false;
  horarioEmEdicaoId: string | null = null;
  mostrarAulasPorLancar = false;
  mostrarAvaliacoesAgendadas = false;
  mostrarFormularioAgendarGeral = false;

  form = this.fb.group({
    alocacao_id: ['', Validators.required],
    dia_semana: [1, Validators.required],
    hora_inicio: ['08:00', Validators.required],
    hora_fim: ['09:00', Validators.required],
    sala: [''],
  });

  // "Geral" = toda a escola — ver store/diario::agendarAvaliacaoGeral.
  // tipo_avaliacao só oferece os que exigem agendamento (ex.: Prova) —
  // não faz sentido "agendar" um tipo Contínua com hora/sala.
  agendarGeralForm = this.fb.group({
    periodo_avaliacao: ['', Validators.required],
    titulo: ['', Validators.required],
    tipo_avaliacao: ['', Validators.required],
    peso: [100, [Validators.required, Validators.min(0.01)]],
    data_avaliacao: ['', Validators.required],
    hora_inicio: ['', Validators.required],
    hora_fim: ['', Validators.required],
    sala: [''],
    data_limite_correcao: [''],
  });

  ngOnInit() {
    this.store.dispatch(carregarTurmas());
    this.store.dispatch(carregarAlocacoes());
    this.store.dispatch(carregarMinhaGrade());
    this.store.dispatch(carregarPeriodos());
    this.store.dispatch(carregarTiposAvaliacao());

    // Sempre que o professor/disciplina escolhido no formulário muda,
    // vai buscar a grade horária desse professor — para a "ocupação em
    // tempo real" (ver template) mostrar logo os horários que ele já
    // tem marcados, antes de a Secretária tentar gravar um conflito.
    this.subscricoes.add(
      this.form.controls.alocacao_id.valueChanges.subscribe(alocacaoId => {
        if (!alocacaoId) {
          this.store.dispatch(limparGradeDoProfessor());
          return;
        }
        this.alocacoes$.pipe(take(1)).subscribe(alocacoes => {
          const alocacao = alocacoes.find(a => a.id === alocacaoId);
          if (alocacao) {
            this.store.dispatch(carregarGradeDoProfessor({ professor_id: alocacao.professor_id }));
          }
        });
      })
    );
  }

  ngOnDestroy() {
    this.subscricoes.unsubscribe();
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
    this.store.dispatch(limparGradeDoProfessor());
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
    this.store.dispatch(limparGradeDoProfessor());
  }

  // Slots já ocupados (do professor ou da turma) no dia escolhido no
  // formulário, excluindo o próprio slot em edição (senão "colidiria
  // consigo mesmo") — usado para mostrar a ocupação em tempo real.
  ocupacaoNoDia(grade: HorarioAula[] | null, dia: number): HorarioAula[] {
    return this.slotsDoDia(grade, dia).filter(s => s.id !== this.horarioEmEdicaoId);
  }

  // Dentro da ocupação do dia, só os que realmente se cruzam com o
  // horário que está a ser preenchido (mesma matemática do back-end) —
  // usado para distinguir "isto vai bater certo" de "só para saberes,
  // há outra aula nesse dia" na grelha de ocupação em tempo real.
  haColisaoDeHorario(slot: HorarioAula): boolean {
    const inicio = this.form.value.hora_inicio;
    const fim = this.form.value.hora_fim;
    if (!inicio || !fim) return false;
    return this.formatarHora(slot.hora_inicio) < fim && this.formatarHora(slot.hora_fim) > inicio;
  }

  alternarAulasPorLancar() {
    this.mostrarAulasPorLancar = !this.mostrarAulasPorLancar;
    if (this.mostrarAulasPorLancar) {
      this.store.dispatch(carregarAulasPorLancar());
    }
  }

  formatarData(data: string): string {
    const [ano, mes, dia] = data.split('-');
    return `${dia}/${mes}/${ano}`;
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

  // --- Avaliações/exames agendados (Geral ou por turma) ---

  alternarAvaliacoesAgendadas() {
    this.mostrarAvaliacoesAgendadas = !this.mostrarAvaliacoesAgendadas;
    if (this.mostrarAvaliacoesAgendadas) {
      this.store.dispatch(carregarAvaliacoesAgendadas({ data_inicio: null, data_fim: null }));
    }
  }

  // Só os tipos marcados "requer_agendamento" (ex.: Prova) fazem
  // sentido aqui — agendar hora/sala para um tipo Contínua não teria efeito.
  tiposParaAgendarGeral(tipos: { id: string; nome: string; requer_agendamento: boolean }[] | null): { id: string; nome: string; requer_agendamento: boolean }[] {
    if (!tipos) return [];
    return tipos.filter(t => t.requer_agendamento);
  }

  alternarFormularioAgendarGeral() {
    this.mostrarFormularioAgendarGeral = !this.mostrarFormularioAgendarGeral;
    this.agendarGeralForm.reset({
      periodo_avaliacao: '', titulo: '', tipo_avaliacao: '', peso: 100,
      data_avaliacao: '', hora_inicio: '', hora_fim: '', sala: '', data_limite_correcao: ''
    });
  }

  onSubmitAgendarGeral() {
    if (this.agendarGeralForm.invalid) return;
    const { periodo_avaliacao, titulo, tipo_avaliacao, peso, data_avaliacao, hora_inicio, hora_fim, sala, data_limite_correcao } = this.agendarGeralForm.value;
    this.store.dispatch(agendarAvaliacaoGeral({
      periodo_avaliacao: periodo_avaliacao!, titulo: titulo!, tipo_avaliacao: tipo_avaliacao!, peso: peso!,
      data_avaliacao: data_avaliacao!, hora_inicio: hora_inicio!, hora_fim: hora_fim!,
      sala: sala || null, data_limite_correcao: data_limite_correcao || null
    }));
    this.mostrarFormularioAgendarGeral = false;
  }
}
