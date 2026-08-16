import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as HorariosActions from './horarios.actions';
import { AulaPorLancar, HorarioAula } from './horarios.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class HorariosEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarGradeDaTurma$ = createEffect(() =>
    this.actions$.pipe(
      ofType(HorariosActions.carregarGradeDaTurma),
      switchMap(action => this.http.get<HorarioAula[]>(`/api/v1/horarios/turmas/${action.turma_id}`).pipe(
        map(horarios => HorariosActions.carregarGradeDaTurmaSucesso({ horarios })),
        catchError(err => of(HorariosActions.horariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar a grade horária desta turma.'
        })))
      ))
    )
  );

  carregarMinhaGrade$ = createEffect(() =>
    this.actions$.pipe(
      ofType(HorariosActions.carregarMinhaGrade),
      switchMap(() => this.http.get<HorarioAula[]>('/api/v1/horarios/minha-grade').pipe(
        map(horarios => HorariosActions.carregarMinhaGradeSucesso({ horarios })),
        catchError(err => of(HorariosActions.horariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o seu horário.'
        })))
      ))
    )
  );

  carregarGradeDoProfessor$ = createEffect(() =>
    this.actions$.pipe(
      ofType(HorariosActions.carregarGradeDoProfessor),
      switchMap(action => this.http.get<HorarioAula[]>(`/api/v1/horarios/professores/${action.professor_id}`).pipe(
        map(horarios => HorariosActions.carregarGradeDoProfessorSucesso({ horarios })),
        catchError(err => of(HorariosActions.horariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar a grade horária deste professor.'
        })))
      ))
    )
  );

  carregarAulasPorLancar$ = createEffect(() =>
    this.actions$.pipe(
      ofType(HorariosActions.carregarAulasPorLancar),
      switchMap(() => this.http.get<AulaPorLancar[]>('/api/v1/horarios/aulas-por-lancar').pipe(
        map(aulas => HorariosActions.carregarAulasPorLancarSucesso({ aulas })),
        catchError(err => of(HorariosActions.horariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as aulas por lançar.'
        })))
      ))
    )
  );

  criarHorario$ = createEffect(() =>
    this.actions$.pipe(
      ofType(HorariosActions.criarHorario),
      switchMap(action => this.http.post('/api/v1/horarios', action.dados).pipe(
        switchMap(() => [
          HorariosActions.carregarGradeDaTurma({ turma_id: action.turma_id }),
          HorariosActions.horariosOperacaoSucesso({ mensagem: 'Aula adicionada à grade horária.' })
        ]),
        catchError(err => of(HorariosActions.horariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível adicionar a aula à grade horária.'
        })))
      ))
    )
  );

  atualizarHorario$ = createEffect(() =>
    this.actions$.pipe(
      ofType(HorariosActions.atualizarHorario),
      switchMap(action => this.http.patch(`/api/v1/horarios/${action.horario_id}`, action.dados).pipe(
        switchMap(() => [
          HorariosActions.carregarGradeDaTurma({ turma_id: action.turma_id }),
          HorariosActions.horariosOperacaoSucesso({ mensagem: 'Aula atualizada.' })
        ]),
        catchError(err => of(HorariosActions.horariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar a aula.'
        })))
      ))
    )
  );

  removerHorario$ = createEffect(() =>
    this.actions$.pipe(
      ofType(HorariosActions.removerHorario),
      switchMap(action => this.http.delete(`/api/v1/horarios/${action.horario_id}`).pipe(
        switchMap(() => [
          HorariosActions.carregarGradeDaTurma({ turma_id: action.turma_id }),
          HorariosActions.horariosOperacaoSucesso({ mensagem: 'Aula removida da grade horária.' })
        ]),
        catchError(err => of(HorariosActions.horariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível remover a aula.'
        })))
      ))
    )
  );
}
