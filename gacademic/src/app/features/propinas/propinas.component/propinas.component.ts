import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { Store } from '@ngrx/store';
import { map } from 'rxjs';
import { carregarPropinas, definirPropina, apagarPropina } from '../../../store/propinas/propinas.actions';
import { selectLinhasPropinas, selectPropinasError } from '../../../store/propinas/propinas.selector';
import { LinhaPropina } from '../../../store/propinas/propinas.models';

interface GrupoCurso {
  curso_id: string;
  curso_nome: string;
  series: LinhaPropina[];
}

@Component({
  selector: 'app-propinas.component',
  imports: [CommonModule, AsyncPipe],
  templateUrl: './propinas.component.html',
  styleUrl: './propinas.component.css',
})
export class PropinasComponent implements OnInit {
  private store = inject(Store);

  erro$ = this.store.select(selectPropinasError);

  anoLetivo = new Date().getFullYear();

  // Agrupa a lista plana (uma linha por Curso/Série, ver
  // schemas/propinas.py) por curso — mantém a hierarquia Curso > Série
  // já usada no resto do módulo Académico, para o preço "por curso"
  // (repetir o mesmo valor nas séries todas) e "por classe" (valores
  // diferentes) ficarem os dois óbvios de fazer na mesma tabela.
  grupos$ = this.store.select(selectLinhasPropinas).pipe(
    map(linhas => {
      const porCurso = new Map<string, GrupoCurso>();
      for (const l of linhas) {
        if (!porCurso.has(l.curso_id)) {
          porCurso.set(l.curso_id, { curso_id: l.curso_id, curso_nome: l.curso_nome, series: [] });
        }
        porCurso.get(l.curso_id)!.series.push(l);
      }
      return Array.from(porCurso.values());
    })
  );

  propinaAApagarId: string | null = null;

  ngOnInit() {
    this.carregar();
  }

  private carregar() {
    this.store.dispatch(carregarPropinas({ ano_letivo: this.anoLetivo }));
  }

  onAnoAnterior() {
    this.anoLetivo -= 1;
    this.carregar();
  }

  onAnoSeguinte() {
    this.anoLetivo += 1;
    this.carregar();
  }

  onGuardar(linha: LinhaPropina, valorMensalidade: string, valorMatricula: string) {
    const mensalidade = Number(valorMensalidade);
    if (!valorMensalidade || isNaN(mensalidade) || mensalidade < 0) return;
    const matricula = valorMatricula.trim() === '' ? null : Number(valorMatricula);
    this.store.dispatch(definirPropina({
      serie_ano_id: linha.serie_ano_id, ano_letivo: this.anoLetivo,
      valor_mensalidade: mensalidade, valor_matricula: matricula,
    }));
  }

  onPedirApagar(propinaId: string) {
    this.propinaAApagarId = propinaId;
  }

  onCancelarApagar() {
    this.propinaAApagarId = null;
  }

  onConfirmarApagar(linha: LinhaPropina) {
    if (!linha.propina_id) return;
    this.store.dispatch(apagarPropina({ propina_id: linha.propina_id, serie_ano_id: linha.serie_ano_id }));
    this.propinaAApagarId = null;
  }
}
