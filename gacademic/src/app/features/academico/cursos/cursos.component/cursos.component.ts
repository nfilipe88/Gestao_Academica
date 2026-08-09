import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { carregarCursos, criarCurso } from '../../../../store/academico/academic.actions';
import { selectAcademicoError, selectCursos } from '../../../../store/academico/academic.selector';

@Component({
  selector: 'app-cursos.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe, RouterLink],
  templateUrl: './cursos.component.html',
  styleUrl: './cursos.component.css',
})
export class CursosComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  // Selecionar os cursos do estado global
  cursos$ = this.store.select(selectCursos);
  erro$ = this.store.select(selectAcademicoError);

  cursoForm = this.fb.group({
    nome: ['', Validators.required]
  });

  ngOnInit() {
    // Ao abrir o ecrã, pede à Store para ir buscar os dados ao Back-end
    this.store.dispatch(carregarCursos());
  }

  onSubmit() {
    if (this.cursoForm.valid) {
      this.store.dispatch(criarCurso({ nome: this.cursoForm.value.nome! }));
      this.cursoForm.reset();
    }
  }
}
