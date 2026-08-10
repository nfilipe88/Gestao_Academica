import { createReducer, on } from '@ngrx/store';
import * as MatriculasActions from './matriculas.actions';
import { MatriculaDaTurma } from './matriculas.models';

export interface MatriculasState {
  // Todas as matrículas já carregadas, de todas as turmas visitadas;
  // filtra-se no cliente por turma_id (mesmo padrão de "vinculos" em
  // alunos.reducer.ts).
  porTurma: MatriculaDaTurma[];
  erro: string | null;
}

export const initialState: MatriculasState = {
  porTurma: [],
  erro: null
};

export const matriculasReducer = createReducer(
  initialState,
  on(MatriculasActions.carregarMatriculasDaTurma, MatriculasActions.criarMatricula,
     MatriculasActions.atualizarStatusMatricula,
    (state) => ({ ...state, erro: null })
  ),
  // Substitui só as matrículas desta turma (as de outras turmas já
  // carregadas ficam como estavam).
  on(MatriculasActions.carregarMatriculasDaTurmaSucesso, (state, { turma_id, matriculas }) => ({
    ...state,
    porTurma: [...state.porTurma.filter(m => m.turma_id !== turma_id), ...matriculas]
  })),
  on(MatriculasActions.matriculasOperacaoFalhou, (state, { erro }) => ({ ...state, erro }))
);
