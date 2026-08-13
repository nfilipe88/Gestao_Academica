import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as CrmActions from './crm.actions';
import { FunilEtapa, OportunidadeCRM } from './crm.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class CrmEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarFunil$ = createEffect(() =>
    this.actions$.pipe(
      ofType(CrmActions.carregarFunil),
      switchMap(() => this.http.get<FunilEtapa[]>('/api/v1/crm/funil').pipe(
        map(etapas => CrmActions.carregarFunilSucesso({ etapas })),
        catchError(err => of(CrmActions.crmOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o funil.'
        })))
      ))
    )
  );

  carregarOportunidades$ = createEffect(() =>
    this.actions$.pipe(
      ofType(CrmActions.carregarOportunidades),
      switchMap(() => this.http.get<OportunidadeCRM[]>('/api/v1/crm/oportunidades').pipe(
        map(oportunidades => CrmActions.carregarOportunidadesSucesso({ oportunidades })),
        catchError(err => of(CrmActions.crmOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as oportunidades.'
        })))
      ))
    )
  );

  criarLead$ = createEffect(() =>
    this.actions$.pipe(
      ofType(CrmActions.criarLead),
      switchMap(action => this.http.post('/api/v1/crm/leads', {
        nome_responsavel: action.nome_responsavel,
        email_contato: action.email_contato,
        telefone: action.telefone,
        nome_aluno_candidato: action.nome_aluno_candidato,
        data_nascimento_candidato: action.data_nascimento_candidato,
        origem_lead: action.origem_lead
      }).pipe(
        switchMap(() => [
          CrmActions.carregarOportunidades(),
          CrmActions.crmOperacaoSucesso({ mensagem: 'Lead registado com sucesso.' })
        ]),
        catchError(err => of(CrmActions.crmOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível registar o lead.'
        })))
      ))
    )
  );

  atualizarLead$ = createEffect(() =>
    this.actions$.pipe(
      ofType(CrmActions.atualizarLead),
      switchMap(action => this.http.patch(`/api/v1/crm/leads/${action.lead_id}`, {
        data_nascimento_candidato: action.data_nascimento_candidato
      }).pipe(
        switchMap(() => [
          CrmActions.carregarOportunidades(),
          CrmActions.crmOperacaoSucesso({ mensagem: 'Dados do candidato atualizados.' })
        ]),
        catchError(err => of(CrmActions.crmOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar o lead.'
        })))
      ))
    )
  );

  moverOportunidade$ = createEffect(() =>
    this.actions$.pipe(
      ofType(CrmActions.moverOportunidade),
      switchMap(action => this.http.patch<{ mensagem: string }>(
        `/api/v1/crm/oportunidades/${action.oportunidade_id}/mover`,
        { nova_etapa_id: action.nova_etapa_id }
      ).pipe(
        switchMap(resp => [
          CrmActions.carregarOportunidades(),
          CrmActions.crmOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(CrmActions.crmOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível mover a oportunidade.'
        })))
      ))
    )
  );
}
