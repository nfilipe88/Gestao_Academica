import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { Store } from '@ngrx/store';
import { carregarIndicadores, carregarRiscoEvasao } from '../../../store/indicadores/indicadores.actions';
import { selectAlunosEmRisco, selectIndicadores, selectIndicadoresError } from '../../../store/indicadores/indicadores.selector';
import { selectMoeda } from '../../../store/configuracoes/configuracoes.selector';

@Component({
  selector: 'app-indicadores.component',
  imports: [CommonModule, AsyncPipe],
  templateUrl: './indicadores.component.html',
  styleUrl: './indicadores.component.css',
})
export class IndicadoresComponent implements OnInit {
  private store = inject(Store);

  indicadores$ = this.store.select(selectIndicadores);
  alunosEmRisco$ = this.store.select(selectAlunosEmRisco);
  erro$ = this.store.select(selectIndicadoresError);
  moeda$ = this.store.select(selectMoeda);

  ngOnInit() {
    this.store.dispatch(carregarIndicadores());
    this.store.dispatch(carregarRiscoEvasao());
  }
}
