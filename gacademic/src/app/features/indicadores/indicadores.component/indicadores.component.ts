import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Store } from '@ngrx/store';
import { carregarIndicadores, carregarRiscoEvasao, gerarTrilhaRecuperacao } from '../../../store/indicadores/indicadores.actions';
import {
  selectAGerarTrilhaPorMatricula, selectAlunosEmRisco, selectIndicadores, selectIndicadoresError, selectTrilhasPorMatricula
} from '../../../store/indicadores/indicadores.selector';
import { selectMoeda } from '../../../store/configuracoes/configuracoes.selector';
import { abrirOuTransferirBlob } from '../../../core/utils/abrir-em-nova-aba';

@Component({
  selector: 'app-indicadores.component',
  imports: [CommonModule, AsyncPipe],
  templateUrl: './indicadores.component.html',
  styleUrl: './indicadores.component.css',
})
export class IndicadoresComponent implements OnInit {
  private store = inject(Store);
  private http = inject(HttpClient);

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

  // "Relatório" (PDF) — abre numa aba nova, como qualquer outro PDF da
  // app (mesmo padrão do Cartão de Acesso/Recibo). "Exportar CSV" —
  // não faz sentido "abrir" um CSV numa aba, por isso nunca pré-abre
  // janela nenhuma: abrirOuTransferirBlob(null, ...) vai direto ao
  // download forçado via <a>.
  onExportarRelatorioPdf() {
    const aba = window.open('', '_blank');
    this.http.get('/api/v1/indicadores/relatorio.pdf', { responseType: 'blob' }).subscribe({
      next: (blob) => abrirOuTransferirBlob(aba, blob, 'relatorio-indicadores.pdf'),
      error: () => { if (aba) aba.close(); }
    });
  }

  onExportarRiscoEvasaoCsv() {
    this.http.get('/api/v1/indicadores/risco-evasao/exportar.csv', { responseType: 'blob' }).subscribe({
      next: (blob) => abrirOuTransferirBlob(null, blob, 'risco-evasao.csv'),
    });
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
