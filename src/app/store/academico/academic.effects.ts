import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as AcademicoActions from './academic.actions';
import { map, switchMap, tap } from 'rxjs';

@Injectable()
export class AcademicoEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  // Carregar Cursos do Back-end
  carregarCursos$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.carregarCursos),
      switchMap(() => this.http.get<any[]>('/api/v1/academico/cursos').pipe(
        map(cursos => AcademicoActions.carregarCursosSucesso({ cursos }))
      ))
    )
  );

  // Criar Curso e recarregar a lista a seguir
  criarCurso$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AcademicoActions.criarCurso),
      switchMap(action => this.http.post('/api/v1/academico/cursos', { nome: action.nome }).pipe(
        map(() => AcademicoActions.carregarCursos()) // Dispara ação para buscar a lista atualizada
      ))
    )
  );

  // (A lógica para Turmas seria idêntica a esta)
}
