import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as LmsActions from './lms.actions';
import { LmsAtribuicaoVariante, LmsExameDetalhe, LmsGrupoExame, LmsQuestao, LmsResultadoAlunoExame, MaterialAula } from './lms.models';
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
  // EXAMES (motor online) — grupos de variantes
  // ==========================================
  carregarGruposExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.carregarGruposExame),
      switchMap(action => this.http.get<LmsGrupoExame[]>(`/api/v1/lms/alocacoes/${action.alocacao_id}/grupos-exame`).pipe(
        map(grupos => LmsActions.carregarGruposExameSucesso({ grupos })),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os grupos de exame.'
        })))
      ))
    )
  );

  criarGrupoExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.criarGrupoExame),
      switchMap(action => this.http.post('/api/v1/lms/grupos-exame', {
        alocacao_id: action.alocacao_id, titulo: action.titulo, data_inicio: action.data_inicio, data_fim: action.data_fim,
        duracao_minutos: action.duracao_minutos, baralhar_perguntas: action.baralhar_perguntas, modalidade: action.modalidade,
        periodo_avaliacao: action.periodo_avaliacao, tipo_avaliacao: action.tipo_avaliacao, peso: action.peso,
        variantes: action.variantes
      }).pipe(
        switchMap(() => [
          LmsActions.carregarGruposExame({ alocacao_id: action.alocacao_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: `Grupo "${action.titulo}" criado como rascunho — Gestor/Secretaria inicia quando estiver pronto.` })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar o grupo de exame.'
        })))
      ))
    )
  );

  iniciarGrupoExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.iniciarGrupoExame),
      switchMap(action => this.http.patch(`/api/v1/lms/grupos-exame/${action.grupo_id}/iniciar`, {}).pipe(
        switchMap(() => [
          LmsActions.carregarGruposExame({ alocacao_id: action.alocacao_id }),
          LmsActions.carregarAtribuicoesGrupo({ grupo_id: action.grupo_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Grupo iniciado — alunos já podem começar; distribuição por variante feita automaticamente.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível iniciar o grupo de exame.'
        })))
      ))
    )
  );

  reatribuirVariante$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.reatribuirVariante),
      switchMap(action => this.http.patch(`/api/v1/lms/grupos-exame/${action.grupo_id}/reatribuir`, {
        matricula_id: action.matricula_id, exame_id: action.exame_id
      }).pipe(
        switchMap(() => [
          LmsActions.carregarAtribuicoesGrupo({ grupo_id: action.grupo_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Aluno reatribuído a outra variante.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível reatribuir o aluno.'
        })))
      ))
    )
  );

  apagarGrupoExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.apagarGrupoExame),
      switchMap(action => this.http.delete(`/api/v1/lms/grupos-exame/${action.grupo_id}`).pipe(
        switchMap(() => [
          LmsActions.carregarGruposExame({ alocacao_id: action.alocacao_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Grupo de exame apagado.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível apagar o grupo de exame.'
        })))
      ))
    )
  );

  carregarAtribuicoesGrupo$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.carregarAtribuicoesGrupo),
      switchMap(action => this.http.get<LmsAtribuicaoVariante[]>(`/api/v1/lms/grupos-exame/${action.grupo_id}/atribuicoes`).pipe(
        map(atribuicoes => LmsActions.carregarAtribuicoesGrupoSucesso({ grupo_id: action.grupo_id, atribuicoes })),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar as atribuições do grupo.'
        })))
      ))
    )
  );

  // Continuam por variante individual (ver docstring das ações) —
  // depois de qualquer uma, recarrega os grupos da alocação (o
  // publicado de cada variante aparece dentro de LmsGrupoExame.variantes).
  publicarExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.publicarExame),
      switchMap(action => this.http.patch(`/api/v1/lms/exames/${action.exame_id}/publicar`, {}).pipe(
        switchMap(() => [
          LmsActions.carregarGruposExame({ alocacao_id: action.alocacao_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Variante publicada.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível publicar a variante.'
        })))
      ))
    )
  );

  despublicarExame$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.despublicarExame),
      switchMap(action => this.http.patch(`/api/v1/lms/exames/${action.exame_id}/despublicar`, {}).pipe(
        switchMap(() => [
          LmsActions.carregarGruposExame({ alocacao_id: action.alocacao_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Variante escondida temporariamente.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível despublicar a variante.'
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

  carregarResultadosGrupo$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.carregarResultadosGrupo),
      switchMap(action => this.http.get<LmsResultadoAlunoExame[]>(`/api/v1/lms/grupos-exame/${action.grupo_id}/resultados`).pipe(
        map(resultados => LmsActions.carregarResultadosGrupoSucesso({ grupo_id: action.grupo_id, resultados })),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os resultados do grupo.'
        })))
      ))
    )
  );

  corrigirTentativa$ = createEffect(() =>
    this.actions$.pipe(
      ofType(LmsActions.corrigirTentativa),
      switchMap(action => this.http.post(`/api/v1/lms/exames/${action.exame_id}/tentativas/${action.matricula_id}/corrigir`, {
        correcoes: action.correcoes, nota_obtida_override: action.nota_obtida_override
      }).pipe(
        switchMap(() => [
          LmsActions.carregarResultadosGrupo({ grupo_id: action.grupo_id }),
          LmsActions.lmsOperacaoSucesso({ mensagem: 'Correção guardada — o aluno foi notificado.' })
        ]),
        catchError(err => of(LmsActions.lmsOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível guardar a correção.'
        })))
      ))
    )
  );
}
