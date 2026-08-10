import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { combineLatest, map } from 'rxjs';
import { carregarCursos, carregarSeries, criarCurso, criarSerieAno } from '../../../../store/academico/academic.actions';
import { selectAcademicoError, selectCursos, selectSeries } from '../../../../store/academico/academic.selector';

@Component({
  selector: 'app-cursos.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe],
  templateUrl: './cursos.component.html',
  styleUrl: './cursos.component.css',
})
export class CursosComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  erro$ = this.store.select(selectAcademicoError);

  // Cada curso já com as suas Séries/Anos agrupadas (a API devolve-as
  // separadas; o join é feito aqui no cliente).
  cursos$ = combineLatest([
    this.store.select(selectCursos),
    this.store.select(selectSeries)
  ]).pipe(
    map(([cursos, series]) => cursos.map(curso => ({
      ...curso,
      series: series.filter(serie => serie.curso_id === curso.id)
    })))
  );

  // Qual curso está com o painel de Séries/Anos aberto (só um de cada vez).
  cursoExpandidoId: string | null = null;

  mostrarFormulario = false;

  cursoForm = this.fb.group({
    nome: ['', Validators.required]
  });

  serieForm = this.fb.group({
    nome: ['', Validators.required]
  });

  ngOnInit() {
    // Ao abrir o ecrã, pede à Store para ir buscar os dados ao Back-end
    this.store.dispatch(carregarCursos());
    this.store.dispatch(carregarSeries());
  }

  alternarFormulario() {
    this.mostrarFormulario = !this.mostrarFormulario;
    this.cursoForm.reset();
  }

  onSubmit() {
    if (this.cursoForm.valid) {
      this.store.dispatch(criarCurso({ nome: this.cursoForm.value.nome! }));
      this.cursoForm.reset();
      this.mostrarFormulario = false;
    }
  }

  alternarExpandido(cursoId: string) {
    this.cursoExpandidoId = this.cursoExpandidoId === cursoId ? null : cursoId;
    this.serieForm.reset();
  }

  onSubmitSerie(cursoId: string) {
    if (this.serieForm.valid) {
      this.store.dispatch(criarSerieAno({ curso_id: cursoId, nome: this.serieForm.value.nome! }));
      this.serieForm.reset();
    }
  }
}
