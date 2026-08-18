import { createReducer, on } from '@ngrx/store';
import * as LmsActions from './lms.actions';
import { LmsExame, LmsExameDetalhe, LmsQuestao, LmsResultadoAlunoExame, MaterialAula } from './lms.models';

export interface LmsState {
  materiais: MaterialAula[];
  mensagem: string | null;
  erro: string | null;
  aSugerirConteudo: boolean;
  sugestaoConteudo: string | null;
  bancoQuestoes: LmsQuestao[];
  exames: LmsExame[];
  exameDetalhe: LmsExameDetalhe | null;
  resultadosPorExame: Record<string, LmsResultadoAlunoExame[]>;
}

export const initialState: LmsState = {
  materiais: [],
  mensagem: null,
  erro: null,
  aSugerirConteudo: false,
  sugestaoConteudo: null,
  bancoQuestoes: [],
  exames: [],
  exameDetalhe: null,
  resultadosPorExame: {}
};

export const lmsReducer = createReducer(
  initialState,
  on(LmsActions.carregarMateriais, LmsActions.criarMaterial, LmsActions.atualizarMaterial, LmsActions.apagarMaterial,
     LmsActions.carregarBancoQuestoes, LmsActions.criarQuestao, LmsActions.atualizarQuestao, LmsActions.apagarQuestao,
     LmsActions.carregarExames, LmsActions.criarExame, LmsActions.publicarExame, LmsActions.despublicarExame, LmsActions.apagarExame,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(LmsActions.carregarMateriaisSucesso, (state, { materiais }) => ({ ...state, materiais })),
  on(LmsActions.sugerirConteudo, (state) => ({ ...state, erro: null, aSugerirConteudo: true })),
  on(LmsActions.sugerirConteudoSucesso, (state, { sugestao }) => ({ ...state, aSugerirConteudo: false, sugestaoConteudo: sugestao })),
  on(LmsActions.limparSugestaoConteudo, (state) => ({ ...state, sugestaoConteudo: null })),
  on(LmsActions.carregarBancoQuestoesSucesso, (state, { questoes }) => ({ ...state, bancoQuestoes: questoes })),
  on(LmsActions.carregarExamesSucesso, (state, { exames }) => ({ ...state, exames })),
  on(LmsActions.carregarExameDetalhe, (state) => ({ ...state, erro: null, exameDetalhe: null })),
  on(LmsActions.carregarExameDetalheSucesso, (state, { exame }) => ({ ...state, exameDetalhe: exame })),
  on(LmsActions.limparExameDetalhe, (state) => ({ ...state, exameDetalhe: null })),
  on(LmsActions.carregarResultadosExameSucesso, (state, { exame_id, resultados }) => ({
    ...state, resultadosPorExame: { ...state.resultadosPorExame, [exame_id]: resultados }
  })),
  on(LmsActions.lmsOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(LmsActions.lmsOperacaoFalhou, (state, { erro }) => ({ ...state, erro, aSugerirConteudo: false }))
);
