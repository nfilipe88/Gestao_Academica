import { createReducer, on } from '@ngrx/store';
import * as LmsActions from './lms.actions';
import { LmsAtribuicaoVariante, LmsExameDetalhe, LmsGrupoExame, LmsQuestao, LmsResultadoAlunoExame, MaterialAula } from './lms.models';

export interface LmsState {
  materiais: MaterialAula[];
  mensagem: string | null;
  erro: string | null;
  aSugerirConteudo: boolean;
  sugestaoConteudo: string | null;
  bancoQuestoes: LmsQuestao[];
  grupos: LmsGrupoExame[];
  exameDetalhe: LmsExameDetalhe | null;
  resultadosPorGrupo: Record<string, LmsResultadoAlunoExame[]>;
  atribuicoesPorGrupo: Record<string, LmsAtribuicaoVariante[]>;
}

export const initialState: LmsState = {
  materiais: [],
  mensagem: null,
  erro: null,
  aSugerirConteudo: false,
  sugestaoConteudo: null,
  bancoQuestoes: [],
  grupos: [],
  exameDetalhe: null,
  resultadosPorGrupo: {},
  atribuicoesPorGrupo: {}
};

export const lmsReducer = createReducer(
  initialState,
  on(LmsActions.carregarMateriais, LmsActions.criarMaterial, LmsActions.atualizarMaterial, LmsActions.apagarMaterial,
     LmsActions.carregarBancoQuestoes, LmsActions.criarQuestao, LmsActions.atualizarQuestao, LmsActions.apagarQuestao,
     LmsActions.carregarGruposExame, LmsActions.criarGrupoExame, LmsActions.iniciarGrupoExame, LmsActions.reatribuirVariante,
     LmsActions.publicarExame, LmsActions.despublicarExame, LmsActions.apagarGrupoExame,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(LmsActions.carregarMateriaisSucesso, (state, { materiais }) => ({ ...state, materiais })),
  on(LmsActions.sugerirConteudo, (state) => ({ ...state, erro: null, aSugerirConteudo: true })),
  on(LmsActions.sugerirConteudoSucesso, (state, { sugestao }) => ({ ...state, aSugerirConteudo: false, sugestaoConteudo: sugestao })),
  on(LmsActions.limparSugestaoConteudo, (state) => ({ ...state, sugestaoConteudo: null })),
  on(LmsActions.carregarBancoQuestoesSucesso, (state, { questoes }) => ({ ...state, bancoQuestoes: questoes })),
  on(LmsActions.carregarGruposExameSucesso, (state, { grupos }) => ({ ...state, grupos })),
  on(LmsActions.carregarExameDetalhe, (state) => ({ ...state, erro: null, exameDetalhe: null })),
  on(LmsActions.carregarExameDetalheSucesso, (state, { exame }) => ({ ...state, exameDetalhe: exame })),
  on(LmsActions.limparExameDetalhe, (state) => ({ ...state, exameDetalhe: null })),
  on(LmsActions.carregarResultadosGrupoSucesso, (state, { grupo_id, resultados }) => ({
    ...state, resultadosPorGrupo: { ...state.resultadosPorGrupo, [grupo_id]: resultados }
  })),
  on(LmsActions.carregarAtribuicoesGrupoSucesso, (state, { grupo_id, atribuicoes }) => ({
    ...state, atribuicoesPorGrupo: { ...state.atribuicoesPorGrupo, [grupo_id]: atribuicoes }
  })),
  on(LmsActions.lmsOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(LmsActions.lmsOperacaoFalhou, (state, { erro }) => ({ ...state, erro, aSugerirConteudo: false }))
);
