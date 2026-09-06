import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit, PLATFORM_ID, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { combineLatest, map } from 'rxjs';
import { carregarCursos, carregarTurmas } from '../../../store/academico/academic.actions';
import { selectCursos, selectTurmas } from '../../../store/academico/academic.selector';
import { carregarAlunos } from '../../../store/alunos/alunos.actions';
import { selectPaginacaoAlunos } from '../../../store/alunos/alunos.selector';
import { selectUsuario } from '../../../store/auth/auth.selectors';
import { CHAVE_LOCAL_DICAS_DASHBOARD_FECHADAS, guardarLocal, lerLocal } from '../../../core/utils/armazenamento-local';

interface Dica {
  texto: string;
  link: string;
  rotulo: string;
}

// Sugestões do que explorar, por perfil — pedido direto do utilizador
// ("Quando fazer login na plataforma pode dar algumas dicas e
// sugestões do que o usuario pode fazer ou explorar"). Painel
// dispensável (fecha com "×", preferência guardada em localStorage —
// ver core/utils/armazenamento-local.ts — para não voltar a aparecer
// nesse browser).
const DICAS_POR_PERFIL: Record<string, Dica[]> = {
  GESTOR: [
    { texto: 'Configure o Ano Letivo da escola, se ainda não o fez.', link: '/configuracoes', rotulo: 'Configurações' },
    { texto: 'Explore os indicadores da sua escola em Estatísticas.', link: '/estatisticas', rotulo: 'Estatísticas' },
    { texto: 'Convide a sua equipa em Gestão de Acessos.', link: '/acessos', rotulo: 'Acessos' },
    { texto: 'Configure a Tabela de Propinas da escola.', link: '/propinas', rotulo: 'Propinas' },
  ],
  SECRETARIA: [
    { texto: 'Matricule o primeiro aluno da escola.', link: '/alunos', rotulo: 'Alunos' },
    { texto: 'Acompanhe cobranças e pagamentos em Financeiro.', link: '/financeiro', rotulo: 'Financeiro' },
    { texto: 'Veja as candidaturas recebidas no CRM.', link: '/crm', rotulo: 'CRM' },
  ],
  PROFESSOR: [
    { texto: 'Lance notas e faltas no Diário de Classe.', link: '/diario', rotulo: 'Diário' },
    { texto: 'Publique trabalhos e materiais para as suas turmas.', link: '/comunicacoes', rotulo: 'Comunicações' },
    { texto: 'Consulte o seu Horário de aulas.', link: '/horarios', rotulo: 'Horários' },
  ],
};

@Component({
  selector: 'app-dashboard-home.component',
  imports: [CommonModule, AsyncPipe, RouterLink],
  templateUrl: './dashboard-home.component.html',
  styleUrl: './dashboard-home.component.css',
})
export class DashboardHomeComponent implements OnInit {
  private store = inject(Store);
  private platformId = inject(PLATFORM_ID);

  usuario$ = this.store.select(selectUsuario);

  dicas$ = this.usuario$.pipe(
    map(usuario => (usuario?.perfil_acesso && DICAS_POR_PERFIL[usuario.perfil_acesso]) || [])
  );

  dicasFechadas = signal(lerLocal(this.platformId, CHAVE_LOCAL_DICAS_DASHBOARD_FECHADAS) === '1');

  fecharDicas() {
    this.dicasFechadas.set(true);
    guardarLocal(this.platformId, CHAVE_LOCAL_DICAS_DASHBOARD_FECHADAS, '1');
  }

  resumo$ = combineLatest([
    this.store.select(selectCursos),
    this.store.select(selectTurmas),
    // O total real de alunos vem da paginação (state.total), não do
    // tamanho do array — este só guarda a página atual, e pedimos aqui
    // só 1 (page_size mínimo) porque só precisamos da contagem.
    this.store.select(selectPaginacaoAlunos)
  ]).pipe(
    map(([cursos, turmas, paginacaoAlunos]) => ({
      totalCursos: cursos.length,
      totalTurmas: turmas.length,
      totalAlunos: paginacaoAlunos.total,
      totalVagas: turmas.reduce((soma, turma) => soma + (turma.vagas_maximas ?? 0), 0),
      cursosRecentes: cursos.slice(-5).reverse()
    }))
  );

  ngOnInit() {
    // O ecrã de Cursos/Turmas/Alunos também despacha isto, mas o
    // dashboard pode ser a primeira página aberta (ex.: logo após o
    // login), por isso carrega os dados aqui também. page_size mínimo
    // (10) — só precisamos do total (state.paginacaoAlunos.total),
    // não da lista em si.
    this.store.dispatch(carregarCursos());
    this.store.dispatch(carregarTurmas());
    this.store.dispatch(carregarAlunos({ page_size: 10 }));
  }
}
