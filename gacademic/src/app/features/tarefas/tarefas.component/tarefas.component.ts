import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { combineLatest, map, startWith, Subscription } from 'rxjs';
import { carregarAlocacoes } from '../../../store/professores/professores.actions';
import { selectAlocacoes } from '../../../store/professores/professores.selector';
import { carregarPeriodos } from '../../../store/diario/diario.actions';
import { selectPeriodos } from '../../../store/diario/diario.selector';
import {
  avaliarTarefa, carregarTarefaDetalhe, carregarTarefas, criarTarefa, fecharTarefaDetalhe
} from '../../../store/tarefas/tarefas.actions';
import {
  selectTarefaDetalhe, selectTarefas, selectTarefasError, selectTarefasMensagem
} from '../../../store/tarefas/tarefas.selector';
import { StatusEntrega } from '../../../store/tarefas/tarefas.models';

const STATUS_OPCOES: { valor: StatusEntrega; nome: string }[] = [
  { valor: 'PENDENTE', nome: 'Pendente' },
  { valor: 'ENTREGUE', nome: 'Entregue' },
  { valor: 'ENTREGUE_ATRASADO', nome: 'Entregue (atrasado)' },
  { valor: 'NAO_ENTREGUE', nome: 'Não entregue' },
];

@Component({
  selector: 'app-tarefas.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe],
  templateUrl: './tarefas.component.html',
  styleUrl: './tarefas.component.css',
})
export class TarefasComponent implements OnInit, OnDestroy {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private subscricoes = new Subscription();

  alocacoes$ = this.store.select(selectAlocacoes);
  tarefas$ = this.store.select(selectTarefas);
  tarefaDetalhe$ = this.store.select(selectTarefaDetalhe);
  periodos$ = this.store.select(selectPeriodos);
  erro$ = this.store.select(selectTarefasError);
  mensagem$ = this.store.select(selectTarefasMensagem);

  statusOpcoes = STATUS_OPCOES;

  // Filtro por título, período de avaliação e "só por corrigir" (tem
  // pelo menos uma entrega ainda sem nota) — a lista já vem toda de
  // uma vez para a turma/disciplina selecionada, por isso o filtro é
  // só no cliente.
  filtroForm = this.fb.group({
    busca: [''],
    periodo_avaliacao: [''],
    soPorCorrigir: [false]
  });

  tarefasFiltradas$ = combineLatest([
    this.tarefas$,
    this.filtroForm.valueChanges.pipe(startWith(this.filtroForm.value))
  ]).pipe(
    map(([tarefas, filtro]) => tarefas.filter(t => {
      if (filtro.busca && !t.titulo.toLowerCase().includes(filtro.busca.trim().toLowerCase())) return false;
      if (filtro.periodo_avaliacao && t.periodo_avaliacao !== filtro.periodo_avaliacao) return false;
      if (filtro.soPorCorrigir && t.pendentes === 0) return false;
      return true;
    }))
  );

  limparFiltro() {
    this.filtroForm.reset({ busca: '', periodo_avaliacao: '', soPorCorrigir: false });
  }

  alocacaoSelecionadaId = '';
  turmaSelecionadaId: string | null = null;
  disciplinaSelecionadaId: string | null = null;

  mostrarFormularioTarefa = false;
  tarefaForm = this.fb.group({
    titulo: ['', Validators.required],
    descricao: [''],
    data_entrega: ['', Validators.required],
    valor_maximo: [10, [Validators.required, Validators.min(0.01)]],
    periodo_avaliacao: ['']
  });

  // Rascunho da avaliação em curso — chave é matricula_id. Reposto
  // sempre que a tarefaDetalhe muda (nova tarefa aberta ou lote gravado).
  avaliacoesPorAluno: Record<string, { status: StatusEntrega; nota: number | null; observacoes: string }> = {};

  constructor() {
    this.subscricoes.add(
      this.tarefaDetalhe$.subscribe(tarefa => {
        if (!tarefa) return;
        const rascunho: Record<string, { status: StatusEntrega; nota: number | null; observacoes: string }> = {};
        for (const av of tarefa.avaliacoes) {
          rascunho[av.matricula_id] = { status: av.status, nota: av.nota, observacoes: av.observacoes || '' };
        }
        this.avaliacoesPorAluno = rascunho;
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
    this.mostrarFormularioTarefa = false;
    this.limparFiltro();
    this.store.dispatch(fecharTarefaDetalhe());
    this.alocacoes$.pipe().subscribe(alocacoes => {
      const alocacao = alocacoes.find(a => a.id === alocacaoId);
      if (!alocacao) {
        this.turmaSelecionadaId = null;
        this.disciplinaSelecionadaId = null;
        return;
      }
      this.turmaSelecionadaId = alocacao.turma_id;
      this.disciplinaSelecionadaId = alocacao.disciplina_id;
      this.store.dispatch(carregarTarefas({ turma_id: alocacao.turma_id, disciplina_id: alocacao.disciplina_id }));
    }).unsubscribe();
  }

  alternarFormularioTarefa() {
    this.mostrarFormularioTarefa = !this.mostrarFormularioTarefa;
    this.tarefaForm.reset({ valor_maximo: 10 });
  }

  onSubmitTarefa() {
    if (this.tarefaForm.invalid || !this.alocacaoSelecionadaId || !this.turmaSelecionadaId || !this.disciplinaSelecionadaId) return;
    const { titulo, descricao, data_entrega, valor_maximo, periodo_avaliacao } = this.tarefaForm.value;
    this.store.dispatch(criarTarefa({
      alocacao_id: this.alocacaoSelecionadaId,
      titulo: titulo!,
      descricao: descricao || null,
      data_entrega: data_entrega!,
      valor_maximo: valor_maximo!,
      periodo_avaliacao: periodo_avaliacao || null,
      turma_id: this.turmaSelecionadaId,
      disciplina_id: this.disciplinaSelecionadaId
    }));
    this.mostrarFormularioTarefa = false;
  }

  onAbrirTarefa(tarefaId: string) {
    this.store.dispatch(carregarTarefaDetalhe({ tarefa_id: tarefaId }));
  }

  onFecharTarefa() {
    this.store.dispatch(fecharTarefaDetalhe());
  }

  onNotaChange(matriculaId: string, valorTexto: string) {
    const atual = this.avaliacoesPorAluno[matriculaId] ?? { status: 'PENDENTE' as StatusEntrega, nota: null, observacoes: '' };
    this.avaliacoesPorAluno = {
      ...this.avaliacoesPorAluno,
      [matriculaId]: { ...atual, nota: valorTexto === '' ? null : Number(valorTexto) }
    };
  }

  onStatusChange(matriculaId: string, status: StatusEntrega) {
    const atual = this.avaliacoesPorAluno[matriculaId] ?? { status: 'PENDENTE' as StatusEntrega, nota: null, observacoes: '' };
    this.avaliacoesPorAluno = { ...this.avaliacoesPorAluno, [matriculaId]: { ...atual, status } };
  }

  onObservacoesChange(matriculaId: string, observacoes: string) {
    const atual = this.avaliacoesPorAluno[matriculaId] ?? { status: 'PENDENTE' as StatusEntrega, nota: null, observacoes: '' };
    this.avaliacoesPorAluno = { ...this.avaliacoesPorAluno, [matriculaId]: { ...atual, observacoes } };
  }

  onGuardarAvaliacoes(tarefaId: string) {
    const avaliacoes = Object.entries(this.avaliacoesPorAluno)
      .filter(([, v]) => v.status !== 'PENDENTE')
      .map(([matricula_id, v]) => ({
        matricula_id, status: v.status, nota: v.nota, observacoes: v.observacoes || null
      }));
    if (avaliacoes.length === 0) return;
    this.store.dispatch(avaliarTarefa({ tarefa_id: tarefaId, avaliacoes }));
  }
}
