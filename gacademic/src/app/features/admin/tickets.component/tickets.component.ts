import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import * as AdminActions from '../../../store/admin/admin.actions';
import {
  selectAdminError, selectAdminMensagem, selectPaginacaoTicketsAdmin, selectTicketAtualAdmin, selectTicketsAdmin
} from '../../../store/admin/admin.selector';
import { EstadoTicket } from '../../../store/admin/admin.models';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';

const ROTULOS_ESTADO: Record<EstadoTicket, string> = {
  ABERTO: 'Aberto', EM_ANDAMENTO: 'Em andamento', RESOLVIDO: 'Resolvido', FECHADO: 'Fechado',
};

@Component({
  selector: 'app-tickets.component',
  imports: [AsyncPipe, DatePipe, FormsModule, PaginacaoComponent],
  templateUrl: './tickets.component.html',
  styleUrl: './tickets.component.css',
})
export class TicketsComponent implements OnInit {
  private store = inject(Store);

  tickets$ = this.store.select(selectTicketsAdmin);
  paginacao$ = this.store.select(selectPaginacaoTicketsAdmin);
  ticketAtual$ = this.store.select(selectTicketAtualAdmin);
  mensagem$ = this.store.select(selectAdminMensagem);
  erro$ = this.store.select(selectAdminError);

  readonly estados: EstadoTicket[] = ['ABERTO', 'EM_ANDAMENTO', 'RESOLVIDO', 'FECHADO'];
  readonly rotulosEstado = ROTULOS_ESTADO;

  filtroEstado: EstadoTicket | '' = '';
  ticketAbertoId: string | null = null;
  respostaTexto = '';
  tamanho = 25;

  ngOnInit() {
    this.carregar(1);
  }

  private carregar(pagina: number) {
    this.store.dispatch(AdminActions.carregarTicketsAdmin({
      page: pagina, page_size: this.tamanho, estado: (this.filtroEstado || undefined) as EstadoTicket | undefined
    }));
  }

  onTamanho(tamanho: number) {
    this.tamanho = tamanho;
    this.carregar(1);
  }

  aplicarFiltro() {
    this.carregar(1);
  }

  onAbrirTicket(id: string) {
    this.ticketAbertoId = id;
    this.store.dispatch(AdminActions.carregarTicketAdmin({ id }));
  }

  onFecharTicket() {
    this.ticketAbertoId = null;
    this.carregar(1);
  }

  onEnviarResposta(id: string) {
    if (!this.respostaTexto.trim()) return;
    this.store.dispatch(AdminActions.responderTicketAdmin({ id, corpo: this.respostaTexto }));
    this.respostaTexto = '';
  }

  onAlterarEstado(id: string, estado: string) {
    this.store.dispatch(AdminActions.alterarEstadoTicketAdmin({ id, estado: estado as EstadoTicket }));
  }

  onPagina(pagina: number) {
    this.carregar(pagina);
  }
}
