import { AsyncPipe, CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, inject, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { Subscription, take } from 'rxjs';
import { carregarAlocacoes } from '../../../store/professores/professores.actions';
import { selectAlocacoes } from '../../../store/professores/professores.selector';
import { selectIsGestorOuSecretaria } from '../../../store/auth/auth.selectors';
import { carregarObjetivosAprendizagem } from '../../../store/academico/academic.actions';
import { selectObjetivosAprendizagem } from '../../../store/academico/academic.selector';
import { ObjetivoAprendizagem } from '../../../store/academico/academic.models';
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
import {
  apagarMaterial, atualizarMaterial, carregarMateriais, criarMaterial, limparSugestaoConteudo, sugerirConteudo
} from '../../../store/lms/lms.actions';
import {
  selectASugerirConteudo, selectLmsError, selectLmsMensagem, selectMateriais, selectSugestaoConteudo
} from '../../../store/lms/lms.selector';
import { MaterialAula } from '../../../store/lms/lms.models';

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
  objetivos$ = this.store.select(selectObjetivosAprendizagem);
  materiais$ = this.store.select(selectMateriais);
  erro$ = this.store.select(selectDiarioError);
  mensagem$ = this.store.select(selectDiarioMensagem);
  erroLms$ = this.store.select(selectLmsError);
  mensagemLms$ = this.store.select(selectLmsMensagem);
  aSugerirConteudo$ = this.store.select(selectASugerirConteudo);
  private sugestaoConteudo$ = this.store.select(selectSugestaoConteudo);
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
    data_avaliacao: [''],
    objetivo_aprendizagem_id: ['']
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

  aba: 'chamada' | 'notas' | 'materiais' | 'consolidado' = 'chamada';

  alocacaoSelecionadaId = '';
  turmaSelecionadaId: string | null = null;
  disciplinaSelecionadaId: string | null = null;

  // Materiais de aula (LMS mínimo) — o conteúdo sobre o qual o aluno
  // pode pedir ajuda ao Prof. Virtual no Portal.
  mostrarFormularioMaterial = false;
  materialEmEdicaoId: string | null = null;
  materialForm = this.fb.group({
    titulo: ['', Validators.required],
    corpo: ['', Validators.required],
    objetivo_aprendizagem_id: [''],
    publicado: [true],
    // Não é enviado ao publicar/atualizar — só orienta o Prof. Virtual
    // ao gerar a sugestão de conteúdo (ver onSugerirConteudo).
    instrucoes_sugestao: ['']
  });
  materialAApagarId: string | null = null;
  // Sugestão de conteúdo do Prof. Virtual à espera de confirmação —
  // só se pede confirmação quando já havia texto escrito no Conteúdo,
  // para não perder trabalho do professor sem avisar.
  sugestaoPendente: string | null = null;
  mostrarConfirmSugestao = false;

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

    // Sempre que chega uma sugestão de conteúdo do Prof. Virtual: se o
    // Conteúdo já tinha texto, pede confirmação antes de substituir; se
    // estava vazio, aplica logo (nada a perder).
    this.subscricoes.add(
      this.sugestaoConteudo$.subscribe(sugestao => {
        if (!sugestao) return;
        const corpoAtual = this.materialForm.value.corpo?.trim();
        if (corpoAtual) {
          this.sugestaoPendente = sugestao;
          this.mostrarConfirmSugestao = true;
        } else {
          this.materialForm.patchValue({ corpo: sugestao });
          this.store.dispatch(limparSugestaoConteudo());
        }
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
      this.store.dispatch(carregarObjetivosAprendizagem({ disciplina_id: alocacao.disciplina_id }));
      this.store.dispatch(carregarMateriais({ turma_id: alocacao.turma_id, disciplina_id: alocacao.disciplina_id }));
    });
  }

  objetivosDaDisciplina(objetivos: ObjetivoAprendizagem[] | null): ObjetivoAprendizagem[] {
    if (!objetivos || !this.disciplinaSelecionadaId) return [];
    return objetivos.filter(o => o.disciplina_id === this.disciplinaSelecionadaId);
  }

  nomeObjetivo(objetivos: ObjetivoAprendizagem[] | null, objetivoId: string | null): string | null {
    if (!objetivoId || !objetivos) return null;
    return objetivos.find(o => o.id === objetivoId)?.nome ?? null;
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
    this.avaliacaoForm.reset({ titulo: '', tipo_avaliacao: 'PROVA', peso: 100, data_avaliacao: '', objetivo_aprendizagem_id: '' });
  }

  onEditarAvaliacao(avaliacao: Avaliacao) {
    this.avaliacaoEmEdicaoId = avaliacao.id;
    this.mostrarFormularioAvaliacao = true;
    this.avaliacaoForm.reset({
      titulo: avaliacao.titulo,
      tipo_avaliacao: avaliacao.tipo_avaliacao,
      peso: avaliacao.peso,
      data_avaliacao: avaliacao.data_avaliacao || '',
      objetivo_aprendizagem_id: avaliacao.objetivo_aprendizagem_id || ''
    });
  }

  onSubmitAvaliacao() {
    if (this.avaliacaoForm.invalid || !this.turmaSelecionadaId || !this.disciplinaSelecionadaId || !this.periodoNotasCarregado) return;
    const { titulo, tipo_avaliacao, peso, data_avaliacao, objetivo_aprendizagem_id } = this.avaliacaoForm.value;

    if (this.avaliacaoEmEdicaoId) {
      this.store.dispatch(atualizarAvaliacao({
        avaliacao_id: this.avaliacaoEmEdicaoId,
        turma_id: this.turmaSelecionadaId, disciplina_id: this.disciplinaSelecionadaId, periodo_avaliacao: this.periodoNotasCarregado,
        titulo: titulo!, tipo_avaliacao: tipo_avaliacao!, peso: peso!, data_avaliacao: data_avaliacao || null,
        objetivo_aprendizagem_id: objetivo_aprendizagem_id || null
      }));
    } else {
      this.store.dispatch(criarAvaliacao({
        turma_id: this.turmaSelecionadaId, disciplina_id: this.disciplinaSelecionadaId, periodo_avaliacao: this.periodoNotasCarregado,
        titulo: titulo!, tipo_avaliacao: tipo_avaliacao!, peso: peso!, data_avaliacao: data_avaliacao || null,
        objetivo_aprendizagem_id: objetivo_aprendizagem_id || null
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

  // --- Materiais de aula (LMS mínimo) ---

  alternarFormularioMaterial() {
    this.mostrarFormularioMaterial = !this.mostrarFormularioMaterial;
    this.materialEmEdicaoId = null;
    this.materialForm.reset({ titulo: '', corpo: '', objetivo_aprendizagem_id: '', publicado: true, instrucoes_sugestao: '' });
    this.sugestaoPendente = null;
    this.mostrarConfirmSugestao = false;
  }

  onEditarMaterial(material: MaterialAula) {
    this.materialEmEdicaoId = material.id;
    this.mostrarFormularioMaterial = true;
    this.materialForm.reset({
      titulo: material.titulo,
      corpo: material.corpo,
      objetivo_aprendizagem_id: material.objetivo_aprendizagem_id || '',
      publicado: material.publicado,
      instrucoes_sugestao: ''
    });
    this.sugestaoPendente = null;
    this.mostrarConfirmSugestao = false;
  }

  onSugerirConteudo() {
    const titulo = this.materialForm.value.titulo?.trim();
    if (!titulo || !this.turmaSelecionadaId || !this.disciplinaSelecionadaId) return;
    this.store.dispatch(sugerirConteudo({
      turma_id: this.turmaSelecionadaId,
      disciplina_id: this.disciplinaSelecionadaId,
      titulo,
      objetivo_aprendizagem_id: this.materialForm.value.objetivo_aprendizagem_id || null,
      instrucoes: this.materialForm.value.instrucoes_sugestao?.trim() || null
    }));
  }

  onAplicarSugestao() {
    if (this.sugestaoPendente) {
      this.materialForm.patchValue({ corpo: this.sugestaoPendente });
    }
    this.sugestaoPendente = null;
    this.mostrarConfirmSugestao = false;
    this.store.dispatch(limparSugestaoConteudo());
  }

  onCancelarSugestao() {
    this.sugestaoPendente = null;
    this.mostrarConfirmSugestao = false;
    this.store.dispatch(limparSugestaoConteudo());
  }

  onSubmitMaterial() {
    if (this.materialForm.invalid || !this.turmaSelecionadaId || !this.disciplinaSelecionadaId) return;
    const { titulo, corpo, objetivo_aprendizagem_id, publicado } = this.materialForm.value;

    if (this.materialEmEdicaoId) {
      this.store.dispatch(atualizarMaterial({
        material_id: this.materialEmEdicaoId,
        turma_id: this.turmaSelecionadaId, disciplina_id: this.disciplinaSelecionadaId,
        titulo: titulo!, corpo: corpo!, objetivo_aprendizagem_id: objetivo_aprendizagem_id || null, publicado: publicado ?? true
      }));
    } else {
      this.store.dispatch(criarMaterial({
        turma_id: this.turmaSelecionadaId, disciplina_id: this.disciplinaSelecionadaId,
        titulo: titulo!, corpo: corpo!, objetivo_aprendizagem_id: objetivo_aprendizagem_id || null, publicado: publicado ?? true
      }));
    }
    this.mostrarFormularioMaterial = false;
    this.materialEmEdicaoId = null;
  }

  onPedirApagarMaterial(materialId: string) {
    this.materialAApagarId = materialId;
  }

  onCancelarApagarMaterial() {
    this.materialAApagarId = null;
  }

  onConfirmarApagarMaterial(materialId: string) {
    if (!this.turmaSelecionadaId || !this.disciplinaSelecionadaId) return;
    this.store.dispatch(apagarMaterial({ material_id: materialId, turma_id: this.turmaSelecionadaId, disciplina_id: this.disciplinaSelecionadaId }));
    this.materialAApagarId = null;
  }
}
