import { createReducer, on } from '@ngrx/store';
import * as AlunosActions from './alunos.actions';
import { Aluno, AlunoResponsavelVinculo, Responsavel } from './alunos.models';

export interface AlunosState {
  alunos: Aluno[];
  responsaveis: Responsavel[];
  vinculos: AlunoResponsavelVinculo[];
  erro: string | null;
}

export const initialState: AlunosState = {
  alunos: [],
  responsaveis: [],
  vinculos: [],
  erro: null
};

export const alunosReducer = createReducer(
  initialState,
  on(AlunosActions.carregarAlunos, AlunosActions.criarAluno,
     AlunosActions.carregarResponsaveis, AlunosActions.criarResponsavel,
     AlunosActions.carregarResponsaveisDoAluno, AlunosActions.vincularResponsavel,
    (state) => ({ ...state, erro: null })
  ),
  on(AlunosActions.carregarAlunosSucesso, (state, { alunos }) => ({ ...state, alunos })),
  on(AlunosActions.carregarResponsaveisSucesso, (state, { responsaveis }) => ({ ...state, responsaveis })),
  // Substitui só os vínculos deste aluno (os de outros alunos já
  // carregados ficam como estavam).
  on(AlunosActions.carregarResponsaveisDoAlunoSucesso, (state, { aluno_id, vinculos }) => ({
    ...state,
    vinculos: [...state.vinculos.filter(v => v.aluno_id !== aluno_id), ...vinculos]
  })),
  on(AlunosActions.alunosOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
