import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { Store } from '@ngrx/store';
import { carregarIndicadores } from '../../../store/indicadores/indicadores.actions';
import { selectIndicadores, selectIndicadoresError } from '../../../store/indicadores/indicadores.selector';

@Component({
  selector: 'app-indicadores.component',
  imports: [CommonModule, AsyncPipe],
  templateUrl: './indicadores.component.html',
  styleUrl: './indicadores.component.css',
})
export class IndicadoresComponent implements OnInit {
  private store = inject(Store);

  indicadores$ = this.store.select(selectIndicadores);
  erro$ = this.store.select(selectIndicadoresError);

  ngOnInit() {
    this.store.dispatch(carregarIndicadores());
  }
}
