import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import { BehaviorSubject, switchMap } from 'rxjs';
import { carregarAlunos } from '../../../store/alunos/alunos.actions';
import { selectAlunos } from '../../../store/alunos/alunos.selector';
import * as TransferenciasActions from '../../../store/transferencias/transferencias.actions';
import {
  selectPaginacaoEnviadas, selectPaginacaoRecebidas, selectSolicitacoesEnviadas, selectSolicitacoesRecebidas,
  selectTransferenciasError, selectTransferenciasMensagem
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
  mensagem$ = this.store.select(selectTransferenciasMensagem);
  erro$ = this.store.select(selectTransferenciasError);

  // "Recebidos": pedidos de OUTRAS escolas dirigidos a esta, à espera
  // de Aceitar/Negar — é aqui que a decisão acontece, direta entre
  // instituições (ver docstring de models_transferencias.py). "Enviados":
  // os pedidos que esta escola fez a outras, só consulta. Duas listas
  // com estado PRÓPRIO na store (não uma partilhada) — importa não as
  // confundir, ou criar um pedido enquanto se vê "Recebidos" sobrepõe
  // essa lista com a de "Enviados".
  aba: 'recebidos' | 'enviados' = 'recebidos';
  private aba$ = new BehaviorSubject<'recebidos' | 'enviados'>('recebidos');
  solicitacoes$ = this.aba$.pipe(
    switchMap(aba => aba === 'recebidos' ? this.store.select(selectSolicitacoesRecebidas) : this.store.select(selectSolicitacoesEnviadas))
  );
  paginacao$ = this.aba$.pipe(
    switchMap(aba => aba === 'recebidos' ? this.store.select(selectPaginacaoRecebidas) : this.store.select(selectPaginacaoEnviadas))
  );
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

  solicitacaoARejeitar: string | null = null;
  observacoesRejeicao = '';

  ngOnInit() {
    this.dispatchComFiltro(1);
    // page_size no máximo permitido (100): isto povoa um <select>, não
    // uma tabela paginada — uma escola com mais de 100 alunos só vê os
    // 100 primeiros aqui (limitação conhecida, fora do âmbito desta
    // passagem; precisaria de um combo com pesquisa/autocomplete).
    this.store.dispatch(carregarAlunos({ page_size: 100 }));
  }

  mudarAba(aba: 'recebidos' | 'enviados') {
    if (this.aba === aba) return;
    this.aba = aba;
    this.aba$.next(aba);
    this.pagina = 1;
    this.dispatchComFiltro(1);
  }

  private dispatchComFiltro(pagina: number) {
    if (this.aba === 'recebidos') {
      this.store.dispatch(TransferenciasActions.carregarSolicitacoesRecebidas({ page: pagina, page_size: this.tamanho }));
    } else {
      this.store.dispatch(TransferenciasActions.carregarMinhasSolicitacoes({
        page: pagina, page_size: this.tamanho,
        status: this.filtroStatus || undefined,
        data_inicio: this.filtroDataInicio || undefined,
        data_fim: this.filtroDataFim || undefined
      }));
    }
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

  aceitar(solicitacaoId: string) {
    this.store.dispatch(TransferenciasActions.aprovarSolicitacao({ solicitacao_id: solicitacaoId }));
  }

  abrirRejeicao(solicitacaoId: string) {
    this.solicitacaoARejeitar = solicitacaoId;
    this.observacoesRejeicao = '';
  }

  cancelarRejeicao() {
    this.solicitacaoARejeitar = null;
  }

  confirmarRejeicao() {
    if (!this.solicitacaoARejeitar || !this.observacoesRejeicao.trim()) return;
    this.store.dispatch(TransferenciasActions.rejeitarSolicitacao({
      solicitacao_id: this.solicitacaoARejeitar, observacoes: this.observacoesRejeicao.trim()
    }));
    this.solicitacaoARejeitar = null;
  }
}
