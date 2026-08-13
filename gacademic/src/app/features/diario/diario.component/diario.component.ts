import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { Subscription, take } from 'rxjs';
import { carregarAlocacoes } from '../../../store/professores/professores.actions';
import { selectAlocacoes } from '../../../store/professores/professores.selector';
import { selectIsGestorOuSecretaria } from '../../../store/auth/auth.selectors';
import {
  carregarAlunosDiario, carregarConsolidado, carregarPeriodos, criarPeriodo,
  lancarFrequencias, lancarNotas, reabrirPeriodo, trancarPeriodo
} from '../../../store/diario/diario.actions';
import {
  selectAlunosDiario, selectConsolidado, selectDiarioError, selectDiarioMensagem, selectPeriodos
} from '../../../store/diario/diario.selector';

@Component({
  selector: 'app-diario.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe],
  templateUrl: './diario.component.html',
  styleUrl: './diario.component.css',
})
export class DiarioComponent implements OnInit, OnDestroy {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private subscricoes = new Subscription();

  alocacoes$ = this.store.select(selectAlocacoes);
  alunos$ = this.store.select(selectAlunosDiario);
  consolidado$ = this.store.select(selectConsolidado);
  periodos$ = this.store.select(selectPeriodos);
  erro$ = this.store.select(selectDiarioError);
  mensagem$ = this.store.select(selectDiarioMensagem);
  podeGerir$ = this.store.select(selectIsGestorOuSecretaria);

  mostrarFormularioPeriodo = false;
  periodoForm = this.fb.group({ nome: ['', Validators.required] });

  aba: 'chamada' | 'notas' | 'consolidado' = 'chamada';

  alocacaoSelecionadaId = '';
  turmaSelecionadaId: string | null = null;
  disciplinaSelecionadaId: string | null = null;

  chamadaForm = this.fb.group({
    data_aula: [new Date().toISOString().substring(0, 10), Validators.required],
    quantidade_aulas: [1, [Validators.required, Validators.min(1)]],
    conteudo_programado: ['']
  });
  presencasPorAluno: Record<string, { presenca: boolean; faltas: number }> = {};

  notasForm = this.fb.group({
    periodo_avaliacao: ['', Validators.required],
    tipo_avaliacao: [''],
    data_avaliacao: ['']
  });
  notasPorAluno: Record<string, number | null> = {};

  constructor() {
    // Sempre que a lista de alunos da turma/disciplina muda, prepara os
    // mapas de presença/nota com valores por omissão (mantendo o que já
    // tiver sido editado, se o aluno continuar na lista). Subscrição
    // manual + ngOnDestroy (em vez de takeUntilDestroyed()) para não
    // depender da deteção automática do contexto de injeção, que nesta
    // rota lazy-loaded estava a rebentar com NG0203 mesmo passando um
    // DestroyRef explícito.
    this.subscricoes.add(
      this.alunos$.subscribe(alunos => {
        const novasPresencas: Record<string, { presenca: boolean; faltas: number }> = {};
        const novasNotas: Record<string, number | null> = {};
        for (const aluno of alunos) {
          novasPresencas[aluno.matricula_id] = this.presencasPorAluno[aluno.matricula_id] ?? { presenca: true, faltas: 0 };
          novasNotas[aluno.matricula_id] = this.notasPorAluno[aluno.matricula_id] ?? null;
        }
        this.presencasPorAluno = novasPresencas;
        this.notasPorAluno = novasNotas;
      })
    );
  }

  ngOnInit() {
    this.store.dispatch(carregarAlocacoes());
    this.store.dispatch(carregarPeriodos());
  }

  ngOnDestroy() {
    this.subscricoes.unsubscribe();
  }

  onSelecionarAlocacao(alocacaoId: string) {
    this.alocacaoSelecionadaId = alocacaoId;
    this.alocacoes$.pipe(take(1)).subscribe(alocacoes => {
      const alocacao = alocacoes.find(a => a.id === alocacaoId);
      if (!alocacao) {
        this.turmaSelecionadaId = null;
        this.disciplinaSelecionadaId = null;
        return;
      }
      this.turmaSelecionadaId = alocacao.turma_id;
      this.disciplinaSelecionadaId = alocacao.disciplina_id;
      this.store.dispatch(carregarAlunosDiario({ turma_id: alocacao.turma_id, disciplina_id: alocacao.disciplina_id }));
    });
  }

  onTogglePresenca(matriculaId: string) {
    const atual = this.presencasPorAluno[matriculaId] ?? { presenca: true, faltas: 0 };
    const novaPresenca = !atual.presenca;
    const quantidadeAulas = this.chamadaForm.value.quantidade_aulas || 1;
    this.presencasPorAluno = {
      ...this.presencasPorAluno,
      [matriculaId]: { presenca: novaPresenca, faltas: novaPresenca ? 0 : quantidadeAulas }
    };
  }

  onSubmitChamada() {
    if (this.chamadaForm.invalid || !this.turmaSelecionadaId || !this.disciplinaSelecionadaId) return;
    const { data_aula, quantidade_aulas, conteudo_programado } = this.chamadaForm.value;
    const frequencias = Object.entries(this.presencasPorAluno).map(([matricula_id, v]) => ({
      matricula_id, presenca: v.presenca, faltas: v.faltas
    }));
    this.store.dispatch(lancarFrequencias({
      turma_id: this.turmaSelecionadaId,
      disciplina_id: this.disciplinaSelecionadaId,
      data_aula: data_aula!,
      quantidade_aulas: quantidade_aulas!,
      conteudo_programado: conteudo_programado || null,
      frequencias
    }));
  }

  onNotaChange(matriculaId: string, valorTexto: string) {
    this.notasPorAluno = {
      ...this.notasPorAluno,
      [matriculaId]: valorTexto === '' ? null : Number(valorTexto)
    };
  }

  onSubmitNotas() {
    if (this.notasForm.invalid || !this.turmaSelecionadaId || !this.disciplinaSelecionadaId) return;
    const { periodo_avaliacao, tipo_avaliacao, data_avaliacao } = this.notasForm.value;
    const notas = Object.entries(this.notasPorAluno)
      .filter((entrada): entrada is [string, number] => entrada[1] !== null)
      .map(([matricula_id, valor_nota]) => ({ matricula_id, valor_nota }));
    if (notas.length === 0) return;

    this.store.dispatch(lancarNotas({
      turma_id: this.turmaSelecionadaId,
      disciplina_id: this.disciplinaSelecionadaId,
      periodo_avaliacao: periodo_avaliacao!,
      tipo_avaliacao: tipo_avaliacao || null,
      data_avaliacao: data_avaliacao || null,
      notas
    }));
  }

  alternarFormularioPeriodo() {
    this.mostrarFormularioPeriodo = !this.mostrarFormularioPeriodo;
    this.periodoForm.reset();
  }

  onSubmitPeriodo() {
    if (this.periodoForm.invalid) return;
    this.store.dispatch(criarPeriodo({ nome: this.periodoForm.value.nome! }));
    this.mostrarFormularioPeriodo = false;
  }

  onTrancarPeriodo(periodoId: string) {
    this.store.dispatch(trancarPeriodo({ periodo_id: periodoId }));
  }

  onReabrirPeriodo(periodoId: string) {
    this.store.dispatch(reabrirPeriodo({ periodo_id: periodoId }));
  }

  onVerConsolidado() {
    if (!this.turmaSelecionadaId || !this.disciplinaSelecionadaId) return;
    this.aba = 'consolidado';
    this.store.dispatch(carregarConsolidado({
      turma_id: this.turmaSelecionadaId,
      disciplina_id: this.disciplinaSelecionadaId,
      periodo_avaliacao: this.notasForm.value.periodo_avaliacao || null
    }));
  }
}
