import { CurrencyPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

interface PlanoSaaSModuloPublico {
  modulo: string;
  preco_adicional: number;
}

interface PlanoSaaSPublico {
  id: string;
  nome: string;
  preco_por_aluno: number;
  limite_alunos: number | null;
  descricao: string | null;
  dias_periodo_teste: number;
  modulos: PlanoSaaSModuloPublico[];
}

/**
 * Não há autenticação nesta página — logo não há tenant, logo não há
 * como saber a moeda da "escola" (não existe nenhuma ainda). Mostra
 * sempre em Kwanza (moeda por omissão da plataforma, ver
 * configuracoes.reducer.ts) — cada escola já registada continua a ver
 * os SEUS próprios valores na moeda que escolheu, dentro da app.
 */
const MOEDA_PUBLICA = 'AOA';

@Component({
  selector: 'app-precos.component',
  imports: [RouterLink, CurrencyPipe],
  templateUrl: './precos.component.html',
  styleUrl: './precos.component.css',
})
export class PrecosComponent implements OnInit {
  private http = inject(HttpClient);

  readonly moeda = MOEDA_PUBLICA;
  planos = signal<PlanoSaaSPublico[]>([]);
  aCarregar = signal(true);
  erro = signal<string | null>(null);

  ngOnInit() {
    this.http.get<PlanoSaaSPublico[]>('/api/v1/public/planos').subscribe({
      next: (planos) => { this.planos.set(planos); this.aCarregar.set(false); },
      error: () => { this.erro.set('Não foi possível carregar os planos neste momento.'); this.aCarregar.set(false); },
    });
  }

  totalModulosAdicionais(plano: PlanoSaaSPublico): number {
    return plano.modulos.filter(m => Number(m.preco_adicional) > 0).length;
  }
}
