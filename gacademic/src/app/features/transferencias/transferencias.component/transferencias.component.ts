import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import { carregarAlunos } from '../../../store/alunos/alunos.actions';
import { selectAlunos } from '../../../store/alunos/alunos.selector';
import * as TransferenciasActions from '../../../store/transferencias/transferencias.actions';
import {
  selectPaginacaoTransferencias, selectSolicitacoesTransferencia, selectTransferenciasError, selectTransferenciasMensagem
} from '../../../store/transferencias/transferencias.selector';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';

@Component({
  selector: 'app-transferencias.component',
  imports: [AsyncPipe, DatePipe, FormsModule, PaginacaoComponent],
  templateUrl: './transferencias.component.html',
  styleUrl: './transferencias.component.css',
})
export class TransferenciasComponent implements OnInit {
  private store = inject(Store);

  alunos$ = this.store.select(selectAlunos);
  solicitacoes$ = this.store.select(selectSolicitacoesTransferencia);
  paginacao$ = this.store.select(selectPaginacaoTransferencias);
  mensagem$ = this.store.select(selectTransferenciasMensagem);
  erro$ = this.store.select(selectTransferenciasError);

  mostrarFormulario = false;
  novoAlunoId = '';
  novoNifDestino = '';
  novoMotivo = '';

  pagina = 1;
  tamanho = 25;

  estados = ['PENDENTE', 'CONCLUIDA', 'REJEITADA'];
  filtroStatus = '';
  filtroDataInicio = '';
  filtroDataFim = '';

  ngOnInit() {
    this.dispatchComFiltro(this.pagina);
    // page_size no máximo permitido (100): isto povoa um <select>, não
    // uma tabela paginada — uma escola com mais de 100 alunos só vê os
    // 100 primeiros aqui (limitação conhecida, fora do âmbito desta
    // passagem; precisaria de um combo com pesquisa/autocomplete).
    this.store.dispatch(carregarAlunos({ page_size: 100 }));
  }

  private dispatchComFiltro(pagina: number) {
    this.store.dispatch(TransferenciasActions.carregarMinhasSolicitacoes({
      page: pagina, page_size: this.tamanho,
      status: this.filtroStatus || undefined,
      data_inicio: this.filtroDataInicio || undefined,
      data_fim: this.filtroDataFim || undefined
    }));
  }

  aplicarFiltro() {
    this.pagina = 1;
    this.dispatchComFiltro(1);
  }

  limparFiltro() {
    this.filtroStatus = '';
    this.filtroDataInicio = '';
    this.filtroDataFim = '';
    this.aplicarFiltro();
  }

  onPagina(pagina: number) {
    this.pagina = pagina;
    this.dispatchComFiltro(pagina);
  }

  onTamanho(tamanho: number) {
    this.tamanho = tamanho;
    this.pagina = 1;
    this.dispatchComFiltro(1);
  }

  onSubmit() {
    if (!this.novoAlunoId || !this.novoNifDestino.trim()) return;
    this.store.dispatch(TransferenciasActions.criarSolicitacao({
      aluno_id: this.novoAlunoId, nif_destino: this.novoNifDestino.trim(), motivo: this.novoMotivo || undefined,
    }));
    this.mostrarFormulario = false;
    this.novoAlunoId = '';
    this.novoNifDestino = '';
    this.novoMotivo = '';
  }
}
