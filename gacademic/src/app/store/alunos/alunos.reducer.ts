import { createReducer, on } from '@ngrx/store';
import * as AlunosActions from './alunos.actions';
import { Aluno, AlunoResponsavelVinculo, Responsavel } from './alunos.models';
import { EstadoPaginacao, PAGINACAO_INICIAL } from '../../shared/models/paginacao.models';

export interface AlunosState {
  alunos: Aluno[];
  paginacaoAlunos: EstadoPaginacao;
  responsaveis: Responsavel[];
  paginacaoResponsaveis: EstadoPaginacao;
  vinculos: AlunoResponsavelVinculo[];
  mensagem: string | null;
  erro: string | null;
}

export const initialState: AlunosState = {
  alunos: [],
  paginacaoAlunos: PAGINACAO_INICIAL,
  responsaveis: [],
  paginacaoResponsaveis: PAGINACAO_INICIAL,
  vinculos: [],
  mensagem: null,
  erro: null
};

export const alunosReducer = createReducer(
  initialState,
  on(AlunosActions.carregarAlunos, AlunosActions.criarAluno,
     AlunosActions.carregarResponsaveis, AlunosActions.criarResponsavel,
     AlunosActions.carregarResponsaveisDoAluno, AlunosActions.vincularResponsavel,
     AlunosActions.criarAcessoAluno, AlunosActions.criarAcessoResponsavel,
    (state) => ({ ...state, erro: null, mensagem: null })
  ),
  on(AlunosActions.carregarAlunosSucesso, (state, { alunos, paginacao }) => ({ ...state, alunos, paginacaoAlunos: paginacao })),
  on(AlunosActions.carregarResponsaveisSucesso, (state, { responsaveis, paginacao }) => ({ ...state, responsaveis, paginacaoResponsaveis: paginacao })),
  // Substitui só os vínculos deste aluno (os de outros alunos já
  // carregados ficam como estavam).
  on(AlunosActions.carregarResponsaveisDoAlunoSucesso, (state, { aluno_id, vinculos }) => ({
    ...state,
    vinculos: [...state.vinculos.filter(v => v.aluno_id !== aluno_id), ...vinculos]
  })),
  on(AlunosActions.alunosOperacaoSucesso, (state, { mensagem }) => ({ ...state, mensagem })),
  on(AlunosActions.alunosOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
