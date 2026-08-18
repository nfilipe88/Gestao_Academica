import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as LmsActions from './lms.actions';
import { LmsExame, LmsExameDetalhe, LmsQuestao, LmsResultadoAlunoExame, MaterialAula } from './lms.models';
import { catchError, map, of, switchMap } from 'rxjs';

@Injectable()
export class LmsEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarMateriais$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.carregarMateriais),
      switchMap(action => this.http.get<MaterialAula[]>(
        `/api/v1/lms/turmas/${action.turma_id}/disciplinas/${action.disciplina_id}/materiais`
      ).pipe(
        map(materiais => LmsActions.carregarMateriaisSucesso({ materiais })),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os materiais de aula.'
        })))
      ))
    )
  );

  criarMaterial$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.criarMaterial),
      switchMap(action => this.http.post('/api/v1/lms/materiais', {
        turma_id: action.turma_id, disciplina_id: action.disciplina_id, titulo: action.titulo, corpo: action.corpo,
        objetivo_aprendizagem_id: action.objetivo_aprendizagem_id, publicado: action.publicado
      }).pipe(
        switchMap(() => [
          LmsActions.carregarMateriais({ turma_id: action.turma_id, disciplina_id: action.disciplina_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: `Material "${action.titulo}" publicado.` })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível publicar o material.'
        })))
      ))
    )
  );

  atualizarMaterial$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.atualizarMaterial),
      switchMap(action => this.http.patch(`/api/v1/lms/materiais/${action.material_id}`, {
        titulo: action.titulo, corpo: action.corpo,
        objetivo_aprendizagem_id: action.objetivo_aprendizagem_id, publicado: action.publicado
      }).pipe(
        switchMap(() => [
          LmsActions.carregarMateriais({ turma_id: action.turma_id, disciplina_id: action.disciplina_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: `Material "${action.titulo}" atualizado.` })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar o material.'
        })))
      ))
    )
  );

  sugerirConteudo$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.sugerirConteudo),
      switchMap(action => this.http.post<{ sugestao: string }>('/api/v1/lms/materiais/sugestao-conteudo', {
        turma_id: action.turma_id, disciplina_id: action.disciplina_id, titulo: action.titulo,
        objetivo_aprendizagem_id: action.objetivo_aprendizagem_id, instrucoes: action.instrucoes
      }).pipe(
        map(resp => LmsActions.sugerirConteudoSucesso({ sugestao: resp.sugestao })),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível gerar uma sugestão de conteúdo.'
        })))
      ))
    )
  );

  apagarMaterial$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.apagarMaterial),
      switchMap(action => this.http.delete(`/api/v1/lms/materiais/${action.material_id}`).pipe(
        switchMap(() => [
          LmsActions.carregarMateriais({ turma_id: action.turma_id, disciplina_id: action.disciplina_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Material apagado.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível apagar o material.'
        })))
      ))
    )
  );

  // ==========================================
  // BANCO DE QUESTÕES
  // ==========================================
  carregarBancoQuestoes$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.carregarBancoQuestoes),
      switchMap(action => this.http.get<LmsQuestao[]>(`/api/v1/lms/disciplinas/${action.disciplina_id}/questoes`).pipe(
        map(questoes => LmsActions.carregarBancoQuestoesSucesso({ questoes })),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o banco de questões.'
        })))
      ))
    )
  );

  criarQuestao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.criarQuestao),
      switchMap(action => this.http.post('/api/v1/lms/questoes', {
        disciplina_id: action.disciplina_id, enunciado: action.enunciado, tipo: action.tipo,
        opcoes: action.opcoes, resposta_correta: action.resposta_correta, valor: action.valor
      }).pipe(
        switchMap(() => [
          LmsActions.carregarBancoQuestoes({ disciplina_id: action.disciplina_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Questão criada.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar a questão.'
        })))
      ))
    )
  );

  atualizarQuestao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.atualizarQuestao),
      switchMap(action => this.http.patch(`/api/v1/lms/questoes/${action.questao_id}`, {
        enunciado: action.enunciado, tipo: action.tipo, opcoes: action.opcoes,
        resposta_correta: action.resposta_correta, valor: action.valor
      }).pipe(
        switchMap(() => [
          LmsActions.carregarBancoQuestoes({ disciplina_id: action.disciplina_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Questão atualizada.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível atualizar a questão.'
        })))
      ))
    )
  );

  apagarQuestao$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.apagarQuestao),
      switchMap(action => this.http.delete(`/api/v1/lms/questoes/${action.questao_id}`).pipe(
        switchMap(() => [
          LmsActions.carregarBancoQuestoes({ disciplina_id: action.disciplina_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Questão apagada.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível apagar a questão.'
        })))
      ))
    )
  );

  // ==========================================
  // EXAMES (motor online)
  // ==========================================
  carregarExames$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.carregarExames),
      switchMap(action => this.http.get<LmsExame[]>(`/api/v1/lms/alocacoes/${action.alocacao_id}/exames`).pipe(
        map(exames => LmsActions.carregarExamesSucesso({ exames })),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os exames.'
        })))
      ))
    )
  );

  criarExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.criarExame),
      switchMap(action => this.http.post('/api/v1/lms/exames', {
        alocacao_id: action.alocacao_id, titulo: action.titulo, data_inicio: action.data_inicio, data_fim: action.data_fim,
        duracao_minutos: action.duracao_minutos, baralhar_perguntas: action.baralhar_perguntas, questao_ids: action.questao_ids
      }).pipe(
        switchMap(() => [
          LmsActions.carregarExames({ alocacao_id: action.alocacao_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: `Exame "${action.titulo}" criado como rascunho — publique quando estiver pronto.` })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o exame.'
        })))
      ))
    )
  );

  publicarExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.publicarExame),
      switchMap(action => this.http.patch(`/api/v1/lms/exames/${action.exame_id}/publicar`, {}).pipe(
        switchMap(() => [
          LmsActions.carregarExames({ alocacao_id: action.alocacao_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Exame publicado — já visível aos alunos da turma.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível publicar o exame.'
        })))
      ))
    )
  );

  despublicarExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.despublicarExame),
      switchMap(action => this.http.patch(`/api/v1/lms/exames/${action.exame_id}/despublicar`, {}).pipe(
        switchMap(() => [
          LmsActions.carregarExames({ alocacao_id: action.alocacao_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Exame voltou a rascunho.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível despublicar o exame.'
        })))
      ))
    )
  );

  apagarExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.apagarExame),
      switchMap(action => this.http.delete(`/api/v1/lms/exames/${action.exame_id}`).pipe(
        switchMap(() => [
          LmsActions.carregarExames({ alocacao_id: action.alocacao_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Exame apagado.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível apagar o exame.'
        })))
      ))
    )
  );

  carregarExameDetalhe$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.carregarExameDetalhe),
      switchMap(action => this.http.get<LmsExameDetalhe>(`/api/v1/lms/exames/${action.exame_id}`).pipe(
        map(exame => LmsActions.carregarExameDetalheSucesso({ exame })),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o exame.'
        })))
      ))
    )
  );

  carregarResultadosExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.carregarResultadosExame),
      switchMap(action => this.http.get<LmsResultadoAlunoExame[]>(`/api/v1/lms/exames/${action.exame_id}/resultados`).pipe(
        map(resultados => LmsActions.carregarResultadosExameSucesso({ exame_id: action.exame_id, resultados })),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os resultados do exame.'
        })))
      ))
    )
  );
}
