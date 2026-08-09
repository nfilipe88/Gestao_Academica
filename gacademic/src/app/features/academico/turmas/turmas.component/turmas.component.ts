import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { combineLatest, map } from 'rxjs';
import { carregarCursos, carregarTurmas, criarTurma } from '../../../../store/academico/academic.actions';
import { selectAcademicoError, selectCursos, selectTurmas } from '../../../../store/academico/academic.selector';

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

  // O back-end só devolve curso_id em cada turma; juntamos aqui o nome do
  // curso (já carregado para preencher o <select>) para não mostrar UUIDs
  // na tabela.
  turmas$ = combineLatest([
    this.store.select(selectTurmas),
    this.cursos$
  ]).pipe(
    map(([turmas, cursos]) => turmas.map(turma => ({
      ...turma,
      cursoNome: cursos.find(c => c.id === turma.curso_id)?.nome ?? '—'
    })))
  );

  turmaForm = this.fb.group({
    curso_id: ['', Validators.required],
    nome_codigo: ['', Validators.required],
    ano_letivo: [new Date().getFullYear(), [Validators.required, Validators.min(2000)]],
    vagas_maximas: [30, [Validators.required, Validators.min(1)]]
  });

  ngOnInit() {
    // Precisamos dos cursos (para o <select> e para mostrar o nome na
    // tabela) e das turmas já existentes.
    this.store.dispatch(carregarCursos());
    this.store.dispatch(carregarTurmas());
  }

  onSubmit() {
    if (this.turmaForm.invalid) {
      return;
    }
    const { curso_id, nome_codigo, ano_letivo, vagas_maximas } = this.turmaForm.value;
    this.store.dispatch(criarTurma({
      curso_id: curso_id!,
      nome_codigo: nome_codigo!,
      ano_letivo: ano_letivo!,
      vagas_maximas: vagas_maximas!
    }));
    this.turmaForm.reset({
      curso_id: '',
      nome_codigo: '',
      ano_letivo: new Date().getFullYear(),
      vagas_maximas: 30
    });
  }
}
