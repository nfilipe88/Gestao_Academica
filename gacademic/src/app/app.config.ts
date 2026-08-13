import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors, withFetch } from '@angular/common/http';
import { provideStore } from '@ngrx/store';
import { provideEffects } from '@ngrx/effects';

// Importações dos seus ficheiros
import { authReducer } from './store/auth/auth.reducer';
import { AuthEffects } from './store/auth/auth.effects';
import { academicoReducer } from './store/academico/academic.reducer';
import { AcademicoEffects } from './store/academico/academic.effects';
import { alunosReducer } from './store/alunos/alunos.reducer';
import { AlunosEffects } from './store/alunos/alunos.effects';
import { matriculasReducer } from './store/matriculas/matriculas.reducer';
import { MatriculasEffects } from './store/matriculas/matriculas.effects';
import { professoresReducer } from './store/professores/professores.reducer';
import { ProfessoresEffects } from './store/professores/professores.effects';
import { comunicacoesReducer } from './store/comunicacoes/comunicacoes.reducer';
import { ComunicacoesEffects } from './store/comunicacoes/comunicacoes.effects';
import { diarioReducer } from './store/diario/diario.reducer';
import { DiarioEffects } from './store/diario/diario.effects';
import { financeiroReducer } from './store/financeiro/financeiro.reducer';
import { FinanceiroEffects } from './store/financeiro/financeiro.effects';
import { crmReducer } from './store/crm/crm.reducer';
import { CrmEffects } from './store/crm/crm.effects';
import { horariosReducer } from './store/horarios/horarios.reducer';
import { HorariosEffects } from './store/horarios/horarios.effects';
import { routes } from './app.routes';
import { jwtInterceptor } from './core/interceptors/jwt.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withFetch(), withInterceptors([jwtInterceptor])),

    // O NgRx tem de ser providenciado aqui na raiz!
    provideStore({
      auth: authReducer,
      academico: academicoReducer,
      alunos: alunosReducer,
      matriculas: matriculasReducer,
      professores: professoresReducer,
      comunicacoes: comunicacoesReducer,
      diario: diarioReducer,
      financeiro: financeiroReducer,
      crm: crmReducer,
      horarios: horariosReducer
    }),
    provideEffects(AuthEffects, AcademicoEffects, AlunosEffects, MatriculasEffects, ProfessoresEffects, ComunicacoesEffects, DiarioEffects, FinanceiroEffects, CrmEffects, HorariosEffects),
  ]
};
