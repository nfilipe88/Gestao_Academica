import { AsyncPipe, CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, inject, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { Subscription, take } from 'rxjs';
import { carregarAlocacoes } from '../../../store/professores/professores.actions';
import { selectAlocacoes } from '../../../store/professores/professores.selector';
import { selectIsGestorOuSecretaria } from '../../../store/auth/auth.selectors';
import {
  apagarAvaliacao, atualizarAvaliacao, carregarAlunosDiario, carregarAvaliacoes, carregarConsolidado,
  carregarNotasAvaliacao, carregarNotasFinais, carregarPeriodos, criarAvaliacao, criarPeriodo,
  lancarFrequencias, lancarNotas, lancarNotasAvaliacao, reabrirPeriodo, trancarPeriodo
} from '../../../store/diario/diario.actions';
import {
  selectAlunosDiario, selectAvaliacoes, selectConsolidado, selectDiarioError, selectDiarioMensagem,
  selectNotasAvaliacaoSelecionada, selectNotasFinais, selectPeriodos
} from '../../../store/diario/diario.selector';
import { AlunoDiario, Avaliacao, TIPOS_AVALIACAO, TipoAvaliacao } from '../../../store/diario/diario.models';

@Component({
  selector: 'app-diario.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe],
  templateUrl: './diario.component.html',
  styleUrl: './diario.component.css',
})
export class DiarioComponent implements OnInit, OnDestroy {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private cdr = inject(ChangeDetectorRef);
  private subscricoes = new Subscription();

  alocacoes$ = this.store.select(selectAlocacoes);
  alunos$ = this.store.select(selectAlunosDiario);
  consolidado$ = this.store.select(selectConsolidado);
  periodos$ = this.store.select(selectPeriodos);
  avaliacoes$ = this.store.select(selectAvaliacoes);
  notasAvaliacaoSelecionada$ = this.store.select(selectNotasAvaliacaoSelecionada);
  notasFinais$ = this.store.select(selectNotasFinais);
  erro$ = this.store.select(selectDiarioError);
  mensagem$ = this.store.select(selectDiarioMensagem);
  podeGerir$ = this.store.select(selectIsGestorOuSecretaria);

  tiposAvaliacao = TIPOS_AVALIACAO;

  mostrarFormularioPeriodo = false;
  periodoForm = this.fb.group({ nome: ['', Validators.required] });

  // Cópia local dos alunos da turma/disciplina atual — usada para
  // construir os mapas de notas por avaliação (o valor vem de um
  // Observable separado, notasAvaliacaoSelecionada$, por isso
  // precisamos de saber "quem são os alunos" fora do template).
  private alunosAtuais: AlunoDiario[] = [];

  // Avaliações (provas/contínuas) do período atualmente carregado.
  periodoNotasCarregado: string | null = null;
  mostrarFormularioAvaliacao = false;
  avaliacaoEmEdicaoId: string | null = null;
  avaliacaoForm = this.fb.group({
    titulo: ['', Validators.required],
    tipo_avaliacao: ['PROVA' as TipoAvaliacao, Validators.required],
    peso: [100, [Validators.required, Validators.min(0.01)]],
    data_avaliacao: ['']
  });
  avaliacaoAApagarId: string | null = null;
  avaliacaoExpandidaId: string | null = null;
  notasAvaliacaoPorAluno: Record<string, number | null> = {};
  // Falso enquanto o GET .../avaliacoes/{id}/notas ainda não voltou — a
  // tabela de lançamento só é desenhada depois disto ficar True, para
  // não criar os <input> com o mapa ainda vazio (o [value] não voltava
  // a atualizar sozinho quando os dados chegavam a seguir, por a
  // resposta HTTP ser assíncrona e o elemento já ter sido criado).
  avaliacaoNotasProntas = false;

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
        this.alunosAtuais = alunos;
        const novasPresencas: Record<string, { presenca: boolean; faltas: number }> = {};
        const novasNotas: Record<string, number | null> = {};
        for (const aluno of alunos) {
          novasPresencas[aluno.matricula_id] = this.presencasPorAluno[aluno.matricula_id] ?? { presenca: true, faltas: 0 };
          novasNotas[aluno.matricula_id] = this.notasPorAluno[aluno.matricula_id] ?? null;
        }
        this.presencasPorAluno = novasPresencas;
        this.notasPorAluno = novasNotas;
        // Aplicação zoneless (sem zone.js nos polyfills) — mutar campos
        // simples dentro de um .subscribe() manual não agenda sozinho
        // uma verificação; sem isto, o ecrã só atualizava depois de
        // outro evento qualquer (ex.: um clique) acontecer por acaso.
        this.cdr.markForCheck();
      })
    );

    // Pré-preenche o formulário de lançamento por avaliação com as
    // notas já existentes, sempre que se abre/reabre uma avaliação
    // (ver onAlternarLancamento).
    this.subscricoes.add(
      this.notasAvaliacaoSelecionada$.subscribe(notas => {
        const mapa: Record<string, number | null> = {};
        for (const aluno of this.alunosAtuais) {
          const existente = notas.find(n => n.matricula_id === aluno.matricula_id);
          mapa[aluno.matricula_id] = existente ? existente.valor_nota : null;
        }
        this.notasAvaliacaoPorAluno = mapa;
        this.avaliacaoNotasProntas = true;
        this.cdr.markForCheck();
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
      this.periodoNotasCarregado = null;
      this.avaliacaoExpandidaId = null;
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

  // --- Avaliações (provas e contínuas) + nota final calculada ---

  onCarregarPeriodoNotas() {
    const periodo = this.notasForm.value.periodo_avaliacao;
    if (!periodo || !this.turmaSelecionadaId || !this.disciplinaSelecionadaId) return;
    this.periodoNotasCarregado = periodo;
    this.avaliacaoExpandidaId = null;
    this.mostrarFormularioAvaliacao = false;
    this.store.dispatch(carregarAvaliacoes({ turma_id: this.turmaSelecionadaId, disciplina_id: this.disciplinaSelecionadaId, periodo_avaliacao: periodo }));
    this.store.dispatch(carregarNotasFinais({ turma_id: this.turmaSelecionadaId, disciplina_id: this.disciplinaSelecionadaId, periodo_avaliacao: periodo }));
  }

  alternarFormularioAvaliacao() {
    this.mostrarFormularioAvaliacao = !this.mostrarFormularioAvaliacao;
    this.avaliacaoEmEdicaoId = null;
    this.avaliacaoForm.reset({ titulo: '', tipo_avaliacao: 'PROVA', peso: 100, data_avaliacao: '' });
  }

  onEditarAvaliacao(avaliacao: Avaliacao) {
    this.avaliacaoEmEdicaoId = avaliacao.id;
    this.mostrarFormularioAvaliacao = true;
    this.avaliacaoForm.reset({
      titulo: avaliacao.titulo,
      tipo_avaliacao: avaliacao.tipo_avaliacao,
      peso: avaliacao.peso,
      data_avaliacao: avaliacao.data_avaliacao || ''
    });
  }

  onSubmitAvaliacao() {
    if (this.avaliacaoForm.invalid || !this.turmaSelecionadaId || !this.disciplinaSelecionadaId || !this.periodoNotasCarregado) return;
    const { titulo, tipo_avaliacao, peso, data_avaliacao } = this.avaliacaoForm.value;

    if (this.avaliacaoEmEdicaoId) {
      this.store.dispatch(atualizarAvaliacao({
        avaliacao_id: this.avaliacaoEmEdicaoId,
        turma_id: this.turmaSelecionadaId, disciplina_id: this.disciplinaSelecionadaId, periodo_avaliacao: this.periodoNotasCarregado,
        titulo: titulo!, tipo_avaliacao: tipo_avaliacao!, peso: peso!, data_avaliacao: data_avaliacao || null
      }));
    } else {
      this.store.dispatch(criarAvaliacao({
        turma_id: this.turmaSelecionadaId, disciplina_id: this.disciplinaSelecionadaId, periodo_avaliacao: this.periodoNotasCarregado,
        titulo: titulo!, tipo_avaliacao: tipo_avaliacao!, peso: peso!, data_avaliacao: data_avaliacao || null
      }));
    }
    this.mostrarFormularioAvaliacao = false;
    this.avaliacaoEmEdicaoId = null;
  }

  onPedirApagarAvaliacao(avaliacaoId: string) {
    this.avaliacaoAApagarId = avaliacaoId;
  }

  onCancelarApagarAvaliacao() {
    this.avaliacaoAApagarId = null;
  }

  onConfirmarApagarAvaliacao(avaliacaoId: string) {
    if (!this.turmaSelecionadaId || !this.disciplinaSelecionadaId || !this.periodoNotasCarregado) return;
    this.store.dispatch(apagarAvaliacao({
      avaliacao_id: avaliacaoId, turma_id: this.turmaSelecionadaId, disciplina_id: this.disciplinaSelecionadaId, periodo_avaliacao: this.periodoNotasCarregado
    }));
    this.avaliacaoAApagarId = null;
    if (this.avaliacaoExpandidaId === avaliacaoId) this.avaliacaoExpandidaId = null;
  }

  onAlternarLancamento(avaliacaoId: string) {
    this.avaliacaoExpandidaId = this.avaliacaoExpandidaId === avaliacaoId ? null : avaliacaoId;
    if (this.avaliacaoExpandidaId) {
      this.avaliacaoNotasProntas = false;
      this.store.dispatch(carregarNotasAvaliacao({ avaliacao_id: avaliacaoId }));
    }
  }

  onNotaAvaliacaoChange(matriculaId: string, valorTexto: string) {
    this.notasAvaliacaoPorAluno = {
      ...this.notasAvaliacaoPorAluno,
      [matriculaId]: valorTexto === '' ? null : Number(valorTexto)
    };
  }

  onSubmitNotasAvaliacao(avaliacaoId: string) {
    if (!this.turmaSelecionadaId || !this.disciplinaSelecionadaId || !this.periodoNotasCarregado) return;
    const notas = Object.entries(this.notasAvaliacaoPorAluno)
      .filter((entrada): entrada is [string, number] => entrada[1] !== null)
      .map(([matricula_id, valor_nota]) => ({ matricula_id, valor_nota }));
    if (notas.length === 0) return;

    this.store.dispatch(lancarNotasAvaliacao({
      avaliacao_id: avaliacaoId,
      turma_id: this.turmaSelecionadaId, disciplina_id: this.disciplinaSelecionadaId, periodo_avaliacao: this.periodoNotasCarregado,
      notas
    }));
  }
}
