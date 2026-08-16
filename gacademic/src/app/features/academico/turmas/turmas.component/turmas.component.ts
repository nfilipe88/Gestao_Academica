import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { combineLatest, map, startWith } from 'rxjs';
import { carregarCursos, carregarSeries, carregarTurmas, criarTurma } from '../../../../store/academico/academic.actions';
import { selectAcademicoError, selectCursos, selectSeries, selectTurmas } from '../../../../store/academico/academic.selector';
import { carregarAlunos } from '../../../../store/alunos/alunos.actions';
import { selectAlunos } from '../../../../store/alunos/alunos.selector';
import { atualizarStatusMatricula, carregarMatriculasDaTurma, criarMatricula } from '../../../../store/matriculas/matriculas.actions';
import { ESTADOS_MATRICULA } from '../../../../store/matriculas/matriculas.models';
import { selectMatriculasError, selectMatriculasPorTurma } from '../../../../store/matriculas/matriculas.selector';
import { selectIsGestorOuSecretaria } from '../../../../store/auth/auth.selectors';

@Component({
  selector: 'app-turmas.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe, RouterLink],
  templateUrl: './turmas.component.html',
  styleUrl: './turmas.component.css',
})
export class TurmasComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  readonly estadosMatricula = ESTADOS_MATRICULA;

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
    this.store.dispatch(atualizarStatusMatricula({
      matricula_id: matriculaId,
      turma_id: turmaId,
      status_matricula: novoStatus
    }));
  }
}
