import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { combineLatest, map } from 'rxjs';
import { carregarCursos, carregarSeries, carregarTurmas, criarTurma } from '../../../../store/academico/academic.actions';
import { selectAcademicoError, selectCursos, selectSeries, selectTurmas } from '../../../../store/academico/academic.selector';

@Component({
  selector: 'app-turmas.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe, RouterLink],
  templateUrl: './turmas.component.html',
  styleUrl: './turmas.component.css',
})
export class TurmasComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  cursos$ = this.store.select(selectCursos);
  erro$ = this.store.select(selectAcademicoError);

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

  turmas$ = combineLatest([
    this.store.select(selectTurmas),
    this.seriesOptions$
  ]).pipe(
    map(([turmas, seriesOptions]) => turmas.map(turma => ({
      ...turma,
      serieLabel: seriesOptions.find(s => s.id === turma.serie_ano_id)?.label ?? '—'
    })))
  );

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

  turmaForm = this.fb.group({
    serie_ano_id: ['', Validators.required],
    nome_codigo: ['', Validators.required],
    ano_letivo: [new Date().getFullYear(), [Validators.required, Validators.min(2000)]],
    vagas_maximas: [30, [Validators.required, Validators.min(1)]]
  });

  ngOnInit() {
    // Precisamos dos cursos e séries (para o <select> e para mostrar o
    // nome na tabela) e das turmas já existentes.
    this.store.dispatch(carregarCursos());
    this.store.dispatch(carregarSeries());
    this.store.dispatch(carregarTurmas());
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
  }
}
