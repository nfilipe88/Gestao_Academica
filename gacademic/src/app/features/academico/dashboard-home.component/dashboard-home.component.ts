import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { combineLatest, map } from 'rxjs';
import { carregarCursos, carregarTurmas } from '../../../store/academico/academic.actions';
import { selectCursos, selectTurmas } from '../../../store/academico/academic.selector';
import { carregarAlunos } from '../../../store/alunos/alunos.actions';
import { selectPaginacaoAlunos } from '../../../store/alunos/alunos.selector';
import { selectUsuario } from '../../../store/auth/auth.selectors';

@Component({
  selector: 'app-dashboard-home.component',
  imports: [CommonModule, AsyncPipe, RouterLink],
  templateUrl: './dashboard-home.component.html',
  styleUrl: './dashboard-home.component.css',
})
export class DashboardHomeComponent implements OnInit {
  private store = inject(Store);

  usuario$ = this.store.select(selectUsuario);

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
