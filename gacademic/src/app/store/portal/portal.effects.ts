import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as PortalActions from './portal.actions';
import {
  Boletim, EducandoResumo, FinanceiroEducando, HorarioAulaPortal,
  MaterialEducando, MaterialEducandoDetalhe, TarefaEducando
} from './portal.models';
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

  carregarTarefasDoEducando$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.carregarTarefasDoEducando),
      switchMap(action => this.http.get<TarefaEducando[]>(
        `/api/v1/portal/educandos/${action.aluno_id}/tarefas`
      ).pipe(
        map(tarefas => PortalActions.carregarTarefasDoEducandoSucesso({ tarefas })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os trabalhos/tarefas deste educando.'
        })))
      ))
    )
  );

  carregarMateriaisDoEducando$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.carregarMateriaisDoEducando),
      switchMap(action => this.http.get<MaterialEducando[]>(
        `/api/v1/portal/educandos/${action.aluno_id}/materiais`
      ).pipe(
        map(materiais => PortalActions.carregarMateriaisDoEducandoSucesso({ materiais })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os materiais de aula.'
        })))
      ))
    )
  );

  carregarMaterialDoEducando$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.carregarMaterialDoEducando),
      switchMap(action => this.http.get<MaterialEducandoDetalhe>(
        `/api/v1/portal/educandos/${action.aluno_id}/materiais/${action.material_id}`
      ).pipe(
        map(material => PortalActions.carregarMaterialDoEducandoSucesso({ material })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível abrir este material de aula.'
        })))
      ))
    )
  );

  perguntarProfVirtual$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.perguntarProfVirtual),
      switchMap(action => this.http.post<{ resposta: string }>(
        `/api/v1/portal/educandos/${action.aluno_id}/prof-virtual`,
        { material_id: action.material_id, historico: action.historico, pergunta: action.pergunta }
      ).pipe(
        map(resp => PortalActions.perguntarProfVirtualSucesso({ resposta: resp.resposta })),
        catchError(err => of(PortalActions.perguntarProfVirtualFalhou({
          erro: err.error?.detail || 'O Prof. Virtual não conseguiu responder agora.'
        })))
      ))
    )
  );
}
