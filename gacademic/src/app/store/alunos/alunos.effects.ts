import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as AlunosActions from './alunos.actions';
import { Aluno, AlunoResponsavelVinculo, Responsavel } from './alunos.models';
import { PaginaResultado } from '../../shared/models/paginacao.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class AlunosEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  // --- ALUNOS ---
  carregarAlunos$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AlunosActions.carregarAlunos),
      switchMap(action => {
        const params: Record<string, string | number> = { page: action.page ?? 1, page_size: action.page_size ?? 25 };
        if (action.busca) params['busca'] = action.busca;
        if (action.data_nascimento_inicio) params['data_nascimento_inicio'] = action.data_nascimento_inicio;
        if (action.data_nascimento_fim) params['data_nascimento_fim'] = action.data_nascimento_fim;
        return this.http.get<PaginaResultado<Aluno>>('/api/v1/alunos', { params }).pipe(
          map(resp => AlunosActions.carregarAlunosSucesso({
            alunos: resp.items,
            paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
          })),
          catchError(err => of(AlunosActions.alunosOperacaoFalhou({
            erro: err.error?.detail || 'Não foi possível carregar os alunos.'
          })))
        );
      })
    )
  );

  criarAluno$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AlunosActions.criarAluno),
      switchMap(action => this.http.post('/api/v1/alunos', {
        matricula_interna: action.matricula_interna,
        nome_completo: action.nome_completo,
        data_nascimento: action.data_nascimento,
        numero_documento: action.numero_documento
      }).pipe(
        map(() => AlunosActions.carregarAlunos({})), // Atualiza a lista após criar
        catchError(err => of(AlunosActions.alunosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o aluno.'
        })))
      ))
    )
  );

  // --- RESPONSÁVEIS ---
  carregarResponsaveis$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AlunosActions.carregarResponsaveis),
      switchMap(action => this.http.get<PaginaResultado<Responsavel>>('/api/v1/responsaveis', {
        params: { page: action.page ?? 1, page_size: action.page_size ?? 25 }
      }).pipe(
        map(resp => AlunosActions.carregarResponsaveisSucesso({
          responsaveis: resp.items,
          paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
        })),
        catchError(err => of(AlunosActions.alunosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os responsáveis.'
        })))
      ))
    )
  );

  criarResponsavel$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AlunosActions.criarResponsavel),
      switchMap(action => this.http.post('/api/v1/responsaveis', {
        nome_completo: action.nome_completo,
        telefone_contato: action.telefone_contato,
        numero_documento: action.numero_documento,
        email: action.email
      }).pipe(
        map(() => AlunosActions.carregarResponsaveis({})), // Atualiza a lista após criar
        catchError(err => of(AlunosActions.alunosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o responsável.'
        })))
      ))
    )
  );

  // --- VÍNCULO ALUNO <-> RESPONSÁVEL ---
  carregarResponsaveisDoAluno$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AlunosActions.carregarResponsaveisDoAluno),
      switchMap(action => this.http.get<AlunoResponsavelVinculo[]>(`/api/v1/alunos/${action.aluno_id}/responsaveis`).pipe(
        map(vinculos => AlunosActions.carregarResponsaveisDoAlunoSucesso({ aluno_id: action.aluno_id, vinculos })),
        catchError(err => of(AlunosActions.alunosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os responsáveis deste aluno.'
        })))
      ))
    )
  );

  vincularResponsavel$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AlunosActions.vincularResponsavel),
      switchMap(action => this.http.post(`/api/v1/alunos/${action.aluno_id}/responsaveis`, {
        responsavel_id: action.responsavel_id,
        tipo_parentesco: action.tipo_parentesco,
        responsavel_financeiro: action.responsavel_financeiro
      }).pipe(
        // Atualiza só os vínculos deste aluno após vincular
        map(() => AlunosActions.carregarResponsaveisDoAluno({ aluno_id: action.aluno_id })),
        catchError(err => of(AlunosActions.alunosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível vincular o responsável.'
        })))
      ))
    )
  );

  // --- ACESSO AO PORTAL (login próprio para Aluno/Responsável) ---
  criarAcessoAluno$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AlunosActions.criarAcessoAluno),
      switchMap(action => this.http.post<{ mensagem: string }>(`/api/v1/alunos/${action.aluno_id}/criar-acesso`, {
        email: action.email,
        palavra_passe: action.palavra_passe
      }).pipe(
        switchMap(resp => [
          AlunosActions.carregarAlunos({}),
          AlunosActions.alunosOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(AlunosActions.alunosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o acesso ao Portal para este aluno.'
        })))
      ))
    )
  );

  criarAcessoResponsavel$ = createEffect(() =>
    this.actions$.pipe(
      ofType(AlunosActions.criarAcessoResponsavel),
      switchMap(action => this.http.post<{ mensagem: string }>(`/api/v1/responsaveis/${action.responsavel_id}/criar-acesso`, {
        email: action.email,
        palavra_passe: action.palavra_passe
      }).pipe(
        switchMap(resp => [
          AlunosActions.carregarResponsaveis({}),
          AlunosActions.alunosOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(AlunosActions.alunosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o acesso ao Portal para este responsável.'
        })))
      ))
    )
  );
}
