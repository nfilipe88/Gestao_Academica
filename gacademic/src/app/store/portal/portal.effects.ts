import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as PortalActions from './portal.actions';
import { Boletim, EducandoResumo, FinanceiroEducando, HorarioAulaPortal } from './portal.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class PortalEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarMeusEducandos$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.carregarMeusEducandos),
      switchMap(() => this.http.get<EducandoResumo[]>('/api/v1/portal/meus-educandos').pipe(
        map(educandos => PortalActions.carregarMeusEducandosSucesso({ educandos })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os seus educandos.'
        })))
      ))
    )
  );

  carregarHorarioDoEducando$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.carregarHorarioDoEducando),
      switchMap(action => this.http.get<HorarioAulaPortal[]>(
        `/api/v1/portal/educandos/${action.aluno_id}/horario`
      ).pipe(
        map(horario => PortalActions.carregarHorarioDoEducandoSucesso({ horario })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o horário.'
        })))
      ))
    )
  );

  carregarBoletimDoEducando$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.carregarBoletimDoEducando),
      switchMap(action => this.http.get<Boletim>(
        `/api/v1/portal/educandos/${action.aluno_id}/boletim`
      ).pipe(
        map(boletim => PortalActions.carregarBoletimDoEducandoSucesso({ boletim })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o boletim.'
        })))
      ))
    )
  );

  carregarFinanceiroDoEducando$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.carregarFinanceiroDoEducando),
      switchMap(action => this.http.get<FinanceiroEducando>(
        `/api/v1/portal/educandos/${action.aluno_id}/financeiro`
      ).pipe(
        map(financeiro => PortalActions.carregarFinanceiroDoEducandoSucesso({ financeiro })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o financeiro deste educando.'
        })))
      ))
    )
  );
}
