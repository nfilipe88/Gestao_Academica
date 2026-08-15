import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as ProfessoresActions from './professores.actions';
import { Alocacao, Professor } from './professores.models';
import { PaginaResultado } from '../../shared/models/paginacao.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class ProfessoresEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarProfessores$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ProfessoresActions.carregarProfessores),
      switchMap(action => this.http.get<PaginaResultado<Professor>>('/api/v1/professores', {
        params: { page: action.page ?? 1, page_size: action.page_size ?? 25 }
      }).pipe(
        map(resp => ProfessoresActions.carregarProfessoresSucesso({
          professores: resp.items,
          paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
        })),
        catchError(err => of(ProfessoresActions.professoresOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os professores.'
        })))
      ))
    )
  );

  criarProfessor$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ProfessoresActions.criarProfessor),
      switchMap(action => this.http.post('/api/v1/professores', {
        nome_completo: action.nome_completo,
        email: action.email,
        palavra_passe: action.palavra_passe,
        formacao_academica: action.formacao_academica
      }).pipe(
        map(() => ProfessoresActions.carregarProfessores({})), // Atualiza a lista após criar
        catchError(err => of(ProfessoresActions.professoresOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o professor.'
        })))
      ))
    )
  );

  carregarAlocacoes$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ProfessoresActions.carregarAlocacoes),
      switchMap(() => this.http.get<Alocacao[]>('/api/v1/professores/alocacoes/minhas').pipe(
        map(alocacoes => ProfessoresActions.carregarAlocacoesSucesso({ alocacoes })),
        catchError(err => of(ProfessoresActions.professoresOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as alocações.'
        })))
      ))
    )
  );

  criarAlocacao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(ProfessoresActions.criarAlocacao),
      switchMap(action => this.http.post(`/api/v1/professores/${action.professor_id}/alocacoes`, {
        turma_id: action.turma_id,
        disciplina_id: action.disciplina_id
      }).pipe(
        map(() => ProfessoresActions.carregarAlocacoes()),
        catchError(err => of(ProfessoresActions.professoresOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível alocar o professor.'
        })))
      ))
    )
  );
}
