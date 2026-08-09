import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { combineLatest, map } from 'rxjs';
import { carregarCursos, carregarTurmas } from '../../../store/academico/academic.actions';
import { selectCursos, selectTurmas } from '../../../store/academico/academic.selector';
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
    this.store.select(selectTurmas)
  ]).pipe(
    map(([cursos, turmas]) => ({
      totalCursos: cursos.length,
      totalTurmas: turmas.length,
      totalVagas: turmas.reduce((soma, turma) => soma + (turma.vagas_maximas ?? 0), 0),
      cursosRecentes: cursos.slice(-5).reverse()
    }))
  );

  ngOnInit() {
    // O ecrã de Cursos/Turmas também despacha isto, mas o dashboard pode
    // ser a primeira página aberta (ex.: logo após o login), por isso
    // carrega os dados aqui também.
    this.store.dispatch(carregarCursos());
    this.store.dispatch(carregarTurmas());
  }
}
