import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as PortalActions from './portal.actions';
import {
  Boletim, ComunicadoEducando, EducandoResumo, EstatisticasEducando, ExameEducando, FinanceiroEducando,
  HorarioAulaPortal, MaterialEducando, MaterialEducandoDetalhe, ResultadoExame, TarefaEducando, TentativaIniciada
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

  // ==========================================
  // Exames online (LMS)
  // ==========================================
  carregarExamesDoEducando$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.carregarExamesDoEducando),
      switchMap(action => this.http.get<ExameEducando[]>(
        `/api/v1/portal/educandos/${action.aluno_id}/exames`
      ).pipe(
        map(exames => PortalActions.carregarExamesDoEducandoSucesso({ exames })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os exames.'
        })))
      ))
    )
  );

  iniciarTentativaExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.iniciarTentativaExame),
      switchMap(action => this.http.post<TentativaIniciada>(
        `/api/v1/portal/educandos/${action.aluno_id}/exames/${action.exame_id}/iniciar`, {}
      ).pipe(
        map(tentativa => PortalActions.iniciarTentativaExameSucesso({ tentativa })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível iniciar o exame.'
        })))
      ))
    )
  );

  submeterTentativaExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.submeterTentativaExame),
      switchMap(action => this.http.post(
        `/api/v1/portal/educandos/${action.aluno_id}/exames/${action.exame_id}/submeter`,
        { respostas: action.respostas }
      ).pipe(
        switchMap(() => [
          PortalActions.submeterTentativaExameSucesso({ aluno_id: action.aluno_id, exame_id: action.exame_id }),
          PortalActions.carregarExamesDoEducando({ aluno_id: action.aluno_id }),
          PortalActions.carregarResultadoExame({ aluno_id: action.aluno_id, exame_id: action.exame_id })
        ]),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível submeter o exame.'
        })))
      ))
    )
  );

  registarEventoSuspeito$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.registarEventoSuspeito),
      switchMap(action => this.http.post<{ eventos_suspeitos: number }>(
        `/api/v1/portal/educandos/${action.aluno_id}/exames/${action.exame_id}/evento-suspeito`, {}
      ).pipe(
        map(resp => PortalActions.registarEventoSuspeitoSucesso({ eventos_suspeitos: resp.eventos_suspeitos })),
        // Silencioso — perder um evento de proctoring não deve mostrar
        // erro nem atrapalhar o aluno a meio do exame.
        catchError(() => of({ type: '[Portal] Evento Suspeito Ignorado' }))
      ))
    )
  );

  carregarResultadoExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.carregarResultadoExame),
      switchMap(action => this.http.get<ResultadoExame>(
        `/api/v1/portal/educandos/${action.aluno_id}/exames/${action.exame_id}/resultado`
      ).pipe(
        map(resultado => PortalActions.carregarResultadoExameSucesso({ resultado })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o resultado do exame.'
        })))
      ))
    )
  );

  carregarEstatisticasDoEducando$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.carregarEstatisticasDoEducando),
      switchMap(action => this.http.get<EstatisticasEducando>(
        `/api/v1/portal/educandos/${action.aluno_id}/estatisticas`
      ).pipe(
        map(estatisticas => PortalActions.carregarEstatisticasDoEducandoSucesso({ estatisticas })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as estatísticas deste educando.'
        })))
      ))
    )
  );

  carregarComunicadosDoEducando$ = createEffect(() =>
    this.actions$.pipe(
      ofType(PortalActions.carregarComunicadosDoEducando),
      switchMap(action => this.http.get<ComunicadoEducando[]>(
        `/api/v1/portal/educandos/${action.aluno_id}/comunicados`
      ).pipe(
        map(comunicados => PortalActions.carregarComunicadosDoEducandoSucesso({ comunicados })),
        catchError(err => of(PortalActions.portalOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os comunicados deste educando.'
        })))
      ))
    )
  );
}
