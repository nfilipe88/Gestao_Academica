import { AsyncPipe, CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { combineLatest, map, startWith } from 'rxjs';
import { carregarCursos, carregarSeries, carregarTurmas, criarTurma } from '../../../../store/academico/academic.actions';
import { selectAcademicoError, selectCursos, selectSeries, selectTurmas } from '../../../../store/academico/academic.selector';
import { carregarAlunos } from '../../../../store/alunos/alunos.actions';
import { selectAlunos } from '../../../../store/alunos/alunos.selector';
import { atualizarStatusMatricula, carregarMatriculasDaTurma, criarMatricula } from '../../../../store/matriculas/matriculas.actions';
import { ESTADOS_MATRICULA, MatriculaDocumento, MOTIVOS_FIM_CICLO } from '../../../../store/matriculas/matriculas.models';
import { selectMatriculasError, selectMatriculasPorTurma } from '../../../../store/matriculas/matriculas.selector';
import { selectIsGestorOuSecretaria } from '../../../../store/auth/auth.selectors';

@Component({
  selector: 'app-turmas.component',
  imports: [ReactiveFormsModule, FormsModule, CommonModule, AsyncPipe, RouterLink],
  templateUrl: './turmas.component.html',
  styleUrl: './turmas.component.css',
})
export class TurmasComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private http = inject(HttpClient);

  readonly estadosMatricula = ESTADOS_MATRICULA;
  readonly motivosFimCiclo = MOTIVOS_FIM_CICLO;

  cursos$ = this.store.select(selectCursos);
  erro$ = this.store.select(selectAcademicoError);
  matriculasErro$ = this.store.select(selectMatriculasError);
  alunos$ = this.store.select(selectAlunos);

  // Criar turmas, matricular alunos e alterar status de matrícula =
  // GESTOR ou SECRETARIA (ver _PODE_GERIR em academico.py/matriculas.py).
  podeGerir$ = this.store.select(selectIsGestorOuSecretaria);

  // Opções do <select>: cada Série/Ano com "Curso — Série" para dar
  // contexto (o back-end só devolve curso_id, não o nome do curso).
  seriesOptions$ = combineLatest([
    this.store.select(selectSeries),
    this.cursos$
  ]).pipe(
    map(([series, cursos]) => series.map(serie => ({
      ...serie,
      label: `${cursos.find(c => c.id === serie.curso_id)?.nome ?? '—'} — ${serie.nome}`
    })))
  );

  private turmasComLabel$ = combineLatest([
    this.store.select(selectTurmas),
    this.seriesOptions$
  ]).pipe(
    map(([turmas, seriesOptions]) => turmas.map(turma => ({
      ...turma,
      serieLabel: seriesOptions.find(s => s.id === turma.serie_ano_id)?.label ?? '—'
    })))
  );

  // Busca (nome da turma ou curso/série) + filtro por ano letivo — a
  // lista já carrega tudo de uma vez, por isso o filtro é só no cliente.
  filtroForm = this.fb.group({ busca: [''], ano_letivo: [''] });

  anosLetivosDisponiveis$ = this.turmasComLabel$.pipe(
    map(turmas => [...new Set(turmas.map(t => t.ano_letivo))].sort((a, b) => b - a))
  );

  turmas$ = combineLatest([
    this.turmasComLabel$,
    this.filtroForm.valueChanges.pipe(startWith(this.filtroForm.value))
  ]).pipe(
    map(([turmas, filtro]) => turmas.filter(t => {
      if (filtro.ano_letivo && t.ano_letivo !== Number(filtro.ano_letivo)) return false;
      if (filtro.busca) {
        const termo = filtro.busca.trim().toLowerCase();
        if (!t.nome_codigo.toLowerCase().includes(termo) && !t.serieLabel.toLowerCase().includes(termo)) return false;
      }
      return true;
    }))
  );

  limparFiltro() {
    this.filtroForm.reset({ busca: '', ano_letivo: '' });
  }

  // Avisa o utilizador se falta um passo anterior (curso ou série) antes
  // de conseguir criar uma turma.
  avisoSetup$ = combineLatest([
    this.cursos$,
    this.store.select(selectSeries)
  ]).pipe(
    map(([cursos, series]) => {
      if (cursos.length === 0) {
        return 'Ainda não tens nenhum curso registado.';
      }
      if (series.length === 0) {
        return 'Ainda não tens nenhuma Série/Ano registada. Abre um curso e adiciona uma.';
      }
      return null;
    })
  );

  // Qual turma está com o painel de Matrículas aberto (só uma de cada vez).
  turmaExpandidaId: string | null = null;

  mostrarFormulario = false;

  // Alunos matriculados na turma expandida, mais os que ainda não estão
  // matriculados nela (para preencher o <select> de "Matricular aluno").
  matriculasDaTurmaExpandida$ = combineLatest([
    this.store.select(selectMatriculasPorTurma),
    this.alunos$
  ]).pipe(
    map(([matriculas, alunos]) => {
      const daTurma = matriculas.filter(m => m.turma_id === this.turmaExpandidaId);
      const idsMatriculados = new Set(daTurma.map(m => m.aluno_id));
      return {
        matriculadas: daTurma,
        disponiveis: alunos.filter(a => !idsMatriculados.has(a.id))
      };
    })
  );

  turmaForm = this.fb.group({
    serie_ano_id: ['', Validators.required],
    nome_codigo: ['', Validators.required],
    ano_letivo: [new Date().getFullYear(), [Validators.required, Validators.min(2000)]],
    vagas_maximas: [30, [Validators.required, Validators.min(1)]]
  });

  matricularForm = this.fb.group({
    aluno_id: ['', Validators.required],
    ano_letivo: [new Date().getFullYear(), [Validators.required, Validators.min(2000)]]
  });

  ngOnInit() {
    // Precisamos dos cursos e séries (para o <select> e para mostrar o
    // nome na tabela) e das turmas já existentes.
    this.store.dispatch(carregarCursos());
    this.store.dispatch(carregarSeries());
    this.store.dispatch(carregarTurmas());
    this.store.dispatch(carregarAlunos({ page_size: 100 })); // povoa um <select>, ver nota em transferencias.component.ts
  }

  alternarFormulario() {
    this.mostrarFormulario = !this.mostrarFormulario;
    this.turmaForm.reset({
      serie_ano_id: '',
      nome_codigo: '',
      ano_letivo: new Date().getFullYear(),
      vagas_maximas: 30
    });
  }

  onSubmit() {
    if (this.turmaForm.invalid) {
      return;
    }
    const { serie_ano_id, nome_codigo, ano_letivo, vagas_maximas } = this.turmaForm.value;
    this.store.dispatch(criarTurma({
      serie_ano_id: serie_ano_id!,
      nome_codigo: nome_codigo!,
      ano_letivo: ano_letivo!,
      vagas_maximas: vagas_maximas!
    }));
    this.turmaForm.reset({
      serie_ano_id: '',
      nome_codigo: '',
      ano_letivo: new Date().getFullYear(),
      vagas_maximas: 30
    });
    this.mostrarFormulario = false;
  }

  alternarExpandida(turmaId: string) {
    this.turmaExpandidaId = this.turmaExpandidaId === turmaId ? null : turmaId;
    this.matricularForm.reset({ aluno_id: '', ano_letivo: new Date().getFullYear() });
    if (this.turmaExpandidaId) {
      this.store.dispatch(carregarMatriculasDaTurma({ turma_id: this.turmaExpandidaId }));
    }
  }

  onMatricular(turmaId: string) {
    if (this.matricularForm.invalid) return;
    const { aluno_id, ano_letivo } = this.matricularForm.value;
    this.store.dispatch(criarMatricula({
      aluno_id: aluno_id!,
      turma_id: turmaId,
      ano_letivo: ano_letivo!
    }));
    this.matricularForm.reset({ aluno_id: '', ano_letivo: new Date().getFullYear() });
  }

  onAlterarStatus(turmaId: string, matriculaId: string, novoStatus: string) {
    // Fim de Ciclo exige motivo — nunca disparado logo ao escolher no
    // <select>, primeiro mostra o sub-painel de confirmação (ver
    // matriculaEmFimDeCicloId no template). Os outros estados
    // continuam imediatos, como sempre foram.
    if (novoStatus === 'CICLO_CONCLUIDO') {
      this.matriculaEmFimDeCicloId.set(matriculaId);
      return;
    }
    this.store.dispatch(atualizarStatusMatricula({
      matricula_id: matriculaId,
      turma_id: turmaId,
      status_matricula: novoStatus
    }));
  }

  // ==========================================
  // FIM DE CICLO (motivo obrigatório) — ver ESTADOS_VALIDOS/
  // MOTIVOS_FIM_CICLO_VALIDOS em back_end/app/cruds/matriculas.py.
  // ==========================================
  matriculaEmFimDeCicloId = signal<string | null>(null);
  motivoFimCicloEscolhido: Record<string, string> = {};

  onConfirmarFimCiclo(turmaId: string, matriculaId: string) {
    const motivo = this.motivoFimCicloEscolhido[matriculaId];
    if (!motivo) return;
    this.store.dispatch(atualizarStatusMatricula({
      matricula_id: matriculaId, turma_id: turmaId, status_matricula: 'CICLO_CONCLUIDO', motivo
    }));
    this.matriculaEmFimDeCicloId.set(null);
  }

  onCancelarFimCiclo(turmaId: string) {
    this.matriculaEmFimDeCicloId.set(null);
    // Repõe o <select> no estado real — sem isto, a opção "Fim de
    // Ciclo" ficava visualmente escolhida (é o próprio <select> nativo
    // do browser, não muda sozinho só por o pedido nunca ter sido
    // disparado ao back-end).
    this.store.dispatch(carregarMatriculasDaTurma({ turma_id: turmaId }));
  }

  // ==========================================
  // DOCUMENTOS DA MATRÍCULA (sobretudo Reingresso) — pequeno de mais
  // para justificar um slice de NgRx próprio, mesmo padrão de
  // logotipo/site-publico em configuracoes.component.ts.
  // ==========================================
  matriculaDocumentosAbertaId = signal<string | null>(null);
  documentosPorMatricula = signal<Record<string, MatriculaDocumento[]>>({});
  descricaoDocumentoPorMatricula: Record<string, string> = {};
  documentoAEnviarMatriculaId = signal<string | null>(null);

  onAlternarDocumentos(matriculaId: string) {
    const abrir = this.matriculaDocumentosAbertaId() !== matriculaId;
    this.matriculaDocumentosAbertaId.set(abrir ? matriculaId : null);
    if (abrir) {
      this.http.get<MatriculaDocumento[]>(`/api/v1/matriculas/${matriculaId}/documentos`).subscribe({
        next: (documentos) => this.documentosPorMatricula.update(atual => ({ ...atual, [matriculaId]: documentos })),
      });
    }
  }

  onSelecionarDocumento(evento: Event, matriculaId: string) {
    const ficheiro = (evento.target as HTMLInputElement).files?.[0];
    if (!ficheiro) return;
    const dados = new FormData();
    dados.append('ficheiro', ficheiro);
    const descricao = this.descricaoDocumentoPorMatricula[matriculaId] || '';
    this.documentoAEnviarMatriculaId.set(matriculaId);
    this.http.post<{ documentos: MatriculaDocumento[] }>(
      `/api/v1/matriculas/${matriculaId}/documentos?descricao=${encodeURIComponent(descricao)}`, dados
    ).subscribe({
      next: (resp) => {
        this.documentoAEnviarMatriculaId.set(null);
        this.documentosPorMatricula.update(atual => ({ ...atual, [matriculaId]: resp.documentos }));
        this.descricaoDocumentoPorMatricula[matriculaId] = '';
      },
      error: () => this.documentoAEnviarMatriculaId.set(null),
    });
    (evento.target as HTMLInputElement).value = '';
  }

  onRemoverDocumento(matriculaId: string, documentoId: string) {
    this.http.delete<{ documentos: MatriculaDocumento[] }>(
      `/api/v1/matriculas/${matriculaId}/documentos/${documentoId}`
    ).subscribe({
      next: (resp) => this.documentosPorMatricula.update(atual => ({ ...atual, [matriculaId]: resp.documentos })),
    });
  }

  onVerDocumento(matriculaId: string, documentoId: string) {
    const janela = window.open('', '_blank');
    this.http.get<{ url: string }>(`/api/v1/matriculas/${matriculaId}/documentos/${documentoId}/url`).subscribe({
      next: (resp) => {
        janela?.document.write(`<iframe src="${resp.url}" style="border:0;position:fixed;inset:0;width:100%;height:100%"></iframe>`);
      },
      error: () => janela?.close(),
    });
  }
}
