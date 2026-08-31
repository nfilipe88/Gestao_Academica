import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Store } from '@ngrx/store';
import { Actions, ofType } from '@ngrx/effects';
import { carregarDashboardEstatisticas, carregarRelatorioEstatisticas } from '../../../store/estatisticas/estatisticas.actions';
import { selectDashboardEstatisticas, selectEstatisticasError, selectRelatorioEstatisticas } from '../../../store/estatisticas/estatisticas.selector';
import { criarDespesa, criarDespesaSucesso, carregarDespesas, removerDespesa, removerDespesaSucesso } from '../../../store/financeiro/financeiro.actions';
import { selectDespesas, selectFinanceiroError, selectFinanceiroMensagem } from '../../../store/financeiro/financeiro.selector';
import { CATEGORIAS_DESPESA } from '../../../store/financeiro/financeiro.models';
import { selectMoeda } from '../../../store/configuracoes/configuracoes.selector';
import { abrirOuTransferirBlob } from '../../../core/utils/abrir-em-nova-aba';

@Component({
  selector: 'app-estatisticas.component',
  imports: [CommonModule, AsyncPipe, FormsModule],
  templateUrl: './estatisticas.component.html',
  styleUrl: './estatisticas.component.css',
})
export class EstatisticasComponent implements OnInit {
  private store = inject(Store);
  private http = inject(HttpClient);
  private actions$ = inject(Actions);

  dashboard$ = this.store.select(selectDashboardEstatisticas);
  relatorio$ = this.store.select(selectRelatorioEstatisticas);
  erro$ = this.store.select(selectEstatisticasError);
  despesas$ = this.store.select(selectDespesas);
  despesasErro$ = this.store.select(selectFinanceiroError);
  despesasMensagem$ = this.store.select(selectFinanceiroMensagem);
  moeda$ = this.store.select(selectMoeda);

  readonly categoriasDespesa = CATEGORIAS_DESPESA;

  // Por omissão: do primeiro dia do mês corrente até hoje — o período
  // "mais provável" de quem abre o ecrã pela primeira vez.
  dataInicio = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10);
  dataFim = new Date().toISOString().slice(0, 10);

  mostrarFormularioDespesa = false;
  novaDespesa = {
    categoria: 'OUTRO',
    descricao: '',
    valor: null as number | null,
    data_despesa: new Date().toISOString().slice(0, 10),
    forma_pagamento: 'MANUAL',
  };

  ngOnInit() {
    this.store.dispatch(carregarDashboardEstatisticas());
    this.store.dispatch(carregarDespesas({}));
    this.onGerarRelatorio();

    // Uma despesa registada/removida pode cair dentro do período já
    // carregado — só se sabe que a operação terminou (não só que foi
    // pedida) quando a ação de sucesso chega, por isso reage a essa,
    // não a um refresh disparado logo a seguir ao dispatch (que corria
    // à frente do pedido HTTP ainda em curso e mostrava dados velhos).
    this.actions$.pipe(ofType(criarDespesaSucesso, removerDespesaSucesso)).subscribe(() => this.onGerarRelatorio());
  }

  onGerarRelatorio() {
    if (!this.dataInicio || !this.dataFim) return;
    this.store.dispatch(carregarRelatorioEstatisticas({ data_inicio: this.dataInicio, data_fim: this.dataFim }));
  }

  // Mesmo padrão de onExportarRelatorioPdf/onExportarRiscoEvasaoCsv em
  // indicadores.component.ts: .xlsx tenta abrir numa aba pré-aberta
  // (o Excel/LibreOffice normalmente intercepta e oferece "Descarregar
  // e abrir"); .xls é sempre download forçado, tal como o CSV — não
  // faz sentido "ver" um ficheiro binário antigo numa aba do browser.
  onExportarXlsx() {
    const aba = window.open('', '_blank');
    this.http.get(
      `/api/v1/estatisticas/relatorio.xlsx?data_inicio=${this.dataInicio}&data_fim=${this.dataFim}`,
      { responseType: 'blob' }
    ).subscribe({
      next: (blob) => abrirOuTransferirBlob(aba, blob, `estatisticas-${this.dataInicio}-a-${this.dataFim}.xlsx`),
      error: () => { if (aba) aba.close(); }
    });
  }

  onExportarXls() {
    this.http.get(
      `/api/v1/estatisticas/relatorio.xls?data_inicio=${this.dataInicio}&data_fim=${this.dataFim}`,
      { responseType: 'blob' }
    ).subscribe({
      next: (blob) => abrirOuTransferirBlob(null, blob, `estatisticas-${this.dataInicio}-a-${this.dataFim}.xls`),
    });
  }

  onAlternarFormularioDespesa() {
    this.mostrarFormularioDespesa = !this.mostrarFormularioDespesa;
  }

  onRegistarDespesa() {
    if (!this.novaDespesa.descricao.trim() || !this.novaDespesa.valor || this.novaDespesa.valor <= 0) return;
    this.store.dispatch(criarDespesa({
      categoria: this.novaDespesa.categoria,
      descricao: this.novaDespesa.descricao,
      valor: this.novaDespesa.valor,
      data_despesa: this.novaDespesa.data_despesa,
      forma_pagamento: this.novaDespesa.forma_pagamento,
    }));
    this.novaDespesa = {
      categoria: 'OUTRO', descricao: '', valor: null,
      data_despesa: new Date().toISOString().slice(0, 10), forma_pagamento: 'MANUAL',
    };
    this.mostrarFormularioDespesa = false;
  }

  onRemoverDespesa(despesaId: string) {
    this.store.dispatch(removerDespesa({ despesa_id: despesaId }));
  }
}
