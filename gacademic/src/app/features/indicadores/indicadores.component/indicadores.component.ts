import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { Store } from '@ngrx/store';
import { carregarIndicadores, carregarRiscoEvasao, gerarTrilhaRecuperacao } from '../../../store/indicadores/indicadores.actions';
import {
  selectAGerarTrilhaPorMatricula, selectAlunosEmRisco, selectIndicadores, selectIndicadoresError, selectTrilhasPorMatricula
} from '../../../store/indicadores/indicadores.selector';
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
  trilhasPorMatricula$ = this.store.select(selectTrilhasPorMatricula);
  aGerarTrilhaPorMatricula$ = this.store.select(selectAGerarTrilhaPorMatricula);
  erro$ = this.store.select(selectIndicadoresError);
  moeda$ = this.store.select(selectMoeda);

  ngOnInit() {
    this.store.dispatch(carregarIndicadores());
    this.store.dispatch(carregarRiscoEvasao());
  }

  onGerarTrilha(matriculaId: string) {
    this.store.dispatch(gerarTrilhaRecuperacao({ matricula_id: matriculaId }));
  }

  // Mini-formatação do markdown simples que o Prof. Virtual devolve
  // (## títulos, - listas) — sem trazer uma dependência de markdown só
  // para isto, e sem innerHTML (o texto vem da IA, não vale a pena
  // arriscar por um resultado inesperado).
  linhasTrilha(conteudo: string): { tipo: 'titulo' | 'item' | 'texto'; texto: string }[] {
    return conteudo.split('\n').filter(linha => linha.trim().length > 0).map(linha => {
      const aparada = linha.trim();
      if (aparada.startsWith('## ')) return { tipo: 'titulo' as const, texto: aparada.slice(3) };
      if (aparada.startsWith('- ')) return { tipo: 'item' as const, texto: aparada.slice(2) };
      return { tipo: 'texto' as const, texto: aparada };
    });
  }
}
