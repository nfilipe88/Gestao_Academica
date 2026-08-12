import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import * as FinanceiroActions from './financeiro.actions';
import { ContratoFinanceiro, FaturaMensalidade, MatriculaResumo, ResponsavelElegivel } from './financeiro.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class FinanceiroEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarMatriculasDoAluno$ = createEffect(() =>
    this.actions$.pipe(
      ofType(FinanceiroActions.carregarMatriculasDoAluno),
      switchMap(action => this.http.get<any[]>(`/api/v1/alunos/${action.aluno_id}/matriculas`).pipe(
        map(matriculas => FinanceiroActions.carregarMatriculasDoAlunoSucesso({
          matriculas: matriculas.map(m => ({
            matricula_id: m.matricula_id, turma_id: m.turma_id, nome_turma: m.nome_turma,
            status_matricula: m.status_matricula, ano_letivo: m.ano_letivo, data_matricula: m.data_matricula
          } as MatriculaResumo))
        })),
        catchError(err => of(FinanceiroActions.financeiroOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as matrículas deste aluno.'
        })))
      ))
    )
  );

  carregarResponsaveisDaMatricula$ = createEffect(() =>
    this.actions$.pipe(
      ofType(FinanceiroActions.carregarResponsaveisDaMatricula),
      switchMap(action => this.http.get<ResponsavelElegivel[]>(
        `/api/v1/financeiro/matriculas/${action.matricula_id}/responsaveis`
      ).pipe(
        map(responsaveis => FinanceiroActions.carregarResponsaveisDaMatriculaSucesso({ responsaveis })),
        catchError(err => of(FinanceiroActions.financeiroOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os responsáveis deste aluno.'
        })))
      ))
    )
  );

  carregarContratoDaMatricula$ = createEffect(() =>
    this.actions$.pipe(
      ofType(FinanceiroActions.carregarContratoDaMatricula),
      switchMap(action => this.http.get<ContratoFinanceiro>(
        `/api/v1/financeiro/matriculas/${action.matricula_id}/contrato`
      ).pipe(
        switchMap(contrato => [
          FinanceiroActions.carregarContratoDaMatriculaSucesso({ contrato }),
          FinanceiroActions.carregarFaturasDoContrato({ contrato_id: contrato.id })
        ]),
        catchError((err: HttpErrorResponse) => err.status === 404
          ? of(FinanceiroActions.contratoInexistente())
          : of(FinanceiroActions.financeiroOperacaoFalhou({
              erro: err.error?.detail || 'Não foi possível carregar o contrato financeiro.'
            }))
        )
      ))
    )
  );

  criarContrato$ = createEffect(() =>
    this.actions$.pipe(
      ofType(FinanceiroActions.criarContrato),
      switchMap(action => this.http.post<ContratoFinanceiro>('/api/v1/financeiro/contratos', {
        matricula_id: action.matricula_id,
        responsavel_id: action.responsavel_id,
        valor_total_anual: action.valor_total_anual,
        quantidade_parcelas: action.quantidade_parcelas,
        dia_vencimento_padrao: action.dia_vencimento_padrao,
        percentual_desconto_bolsa: action.percentual_desconto_bolsa
      }).pipe(
        switchMap(contrato => [
          FinanceiroActions.carregarContratoDaMatriculaSucesso({ contrato }),
          FinanceiroActions.carregarFaturasDoContrato({ contrato_id: contrato.id }),
          FinanceiroActions.financeiroOperacaoSucesso({ mensagem: 'Contrato financeiro criado com sucesso.' })
        ]),
        catchError(err => of(FinanceiroActions.financeiroOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o contrato financeiro.'
        })))
      ))
    )
  );

  carregarFaturasDoContrato$ = createEffect(() =>
    this.actions$.pipe(
      ofType(FinanceiroActions.carregarFaturasDoContrato),
      switchMap(action => this.http.get<FaturaMensalidade[]>(
        `/api/v1/financeiro/contratos/${action.contrato_id}/faturas`
      ).pipe(
        map(faturas => FinanceiroActions.carregarFaturasDoContratoSucesso({ faturas })),
        catchError(err => of(FinanceiroActions.financeiroOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o extrato financeiro.'
        })))
      ))
    )
  );

  marcarFaturaPaga$ = createEffect(() =>
    this.actions$.pipe(
      ofType(FinanceiroActions.marcarFaturaPaga),
      switchMap(action => this.http.patch<{ mensagem: string }>(
        `/api/v1/financeiro/faturas/${action.fatura_id}/marcar-pago`,
        { valor_pago: action.valor_pago, forma_pagamento: action.forma_pagamento }
      ).pipe(
        switchMap(resp => [
          FinanceiroActions.carregarFaturasDoContrato({ contrato_id: action.contrato_id }),
          FinanceiroActions.financeiroOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(FinanceiroActions.financeiroOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível marcar a fatura como paga.'
        })))
      ))
    )
  );

  processarReguaCobranca$ = createEffect(() =>
    this.actions$.pipe(
      ofType(FinanceiroActions.processarReguaCobranca),
      switchMap(() => this.http.post<{ mensagem: string, emails_enviados: Record<string, number> }>(
        '/api/v1/financeiro/regua-cobranca/processar', {}
      ).pipe(
        map(resp => {
          const total = Object.values(resp.emails_enviados || {}).reduce((soma, valor) => soma + valor, 0);
          return FinanceiroActions.processarReguaCobrancaSucesso({
            mensagem: `Régua de cobrança processada: ${total} e-mail(s) enviado(s).`
          });
        }),
        catchError(err => of(FinanceiroActions.financeiroOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível processar a régua de cobrança.'
        })))
      ))
    )
  );
}
