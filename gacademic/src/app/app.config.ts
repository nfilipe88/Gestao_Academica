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
import { portalReducer } from './store/portal/portal.reducer';
import { PortalEffects } from './store/portal/portal.effects';
import { adminReducer } from './store/admin/admin.reducer';
import { AdminEffects } from './store/admin/admin.effects';
import { tarefasReducer } from './store/tarefas/tarefas.reducer';
import { TarefasEffects } from './store/tarefas/tarefas.effects';
import { indicadoresReducer } from './store/indicadores/indicadores.reducer';
import { IndicadoresEffects } from './store/indicadores/indicadores.effects';
import { notificacoesReducer } from './store/notificacoes/notificacoes.reducer';
import { NotificacoesEffects } from './store/notificacoes/notificacoes.effects';
import { documentosReducer } from './store/documentos/documentos.reducer';
import { DocumentosEffects } from './store/documentos/documentos.effects';
import { transferenciasReducer } from './store/transferencias/transferencias.reducer';
import { TransferenciasEffects } from './store/transferencias/transferencias.effects';
import { configuracoesReducer } from './store/configuracoes/configuracoes.reducer';
import { ConfiguracoesEffects } from './store/configuracoes/configuracoes.effects';
import { lmsReducer } from './store/lms/lms.reducer';
import { LmsEffects } from './store/lms/lms.effects';
import { usuariosReducer } from './store/usuarios/usuarios.reducer';
import { UsuariosEffects } from './store/usuarios/usuarios.effects';
import { perfilReducer } from './store/perfil/perfil.reducer';
import { PerfilEffects } from './store/perfil/perfil.effects';
import { permissoesReducer } from './store/permissoes/permissoes.reducer';
import { PermissoesEffects } from './store/permissoes/permissoes.effects';
import { propinasReducer } from './store/propinas/propinas.reducer';
import { PropinasEffects } from './store/propinas/propinas.effects';
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
      horarios: horariosReducer,
      portal: portalReducer,
      admin: adminReducer,
      tarefas: tarefasReducer,
      indicadores: indicadoresReducer,
      notificacoes: notificacoesReducer,
      documentos: documentosReducer,
      transferencias: transferenciasReducer,
      configuracoes: configuracoesReducer,
      lms: lmsReducer,
      usuarios: usuariosReducer,
      perfil: perfilReducer,
      permissoes: permissoesReducer,
      propinas: propinasReducer
    }),
    provideEffects(AuthEffects, AcademicoEffects, AlunosEffects, MatriculasEffects, ProfessoresEffects, ComunicacoesEffects, DiarioEffects, FinanceiroEffects, CrmEffects, HorariosEffects, PortalEffects, AdminEffects, TarefasEffects, IndicadoresEffects, NotificacoesEffects, DocumentosEffects, TransferenciasEffects, ConfiguracoesEffects, LmsEffects, UsuariosEffects, PerfilEffects, PermissoesEffects, PropinasEffects),
  ]
};
