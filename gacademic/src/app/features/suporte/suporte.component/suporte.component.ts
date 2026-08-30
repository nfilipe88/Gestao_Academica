import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import * as SuporteActions from '../../../store/suporte/suporte.actions';
import {
  selectMeusTickets, selectPaginacaoTickets, selectSuporteErro, selectSuporteMensagem, selectTicketAtual
} from '../../../store/suporte/suporte.selector';
import { EstadoTicket } from '../../../store/suporte/suporte.models';
import { selectUsuario } from '../../../store/auth/auth.selectors';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';

const ROTULOS_ESTADO: Record<EstadoTicket, string> = {
  ABERTO: 'Aberto', EM_ANDAMENTO: 'Em andamento', RESOLVIDO: 'Resolvido', FECHADO: 'Fechado',
};

@Component({
  selector: 'app-suporte.component',
  imports: [ReactiveFormsModule, FormsModule, AsyncPipe, DatePipe, PaginacaoComponent],
  templateUrl: './suporte.component.html',
  styleUrl: './suporte.component.css',
})
export class SuporteComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  tickets$ = this.store.select(selectMeusTickets);
  paginacao$ = this.store.select(selectPaginacaoTickets);
  ticketAtual$ = this.store.select(selectTicketAtual);
  mensagem$ = this.store.select(selectSuporteMensagem);
  erro$ = this.store.select(selectSuporteErro);
  meuUsuario$ = this.store.select(selectUsuario);

  readonly rotulosEstado = ROTULOS_ESTADO;

  mostrarFormularioNovo = false;
  ticketForm = this.fb.group({
    nome: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    assunto: ['', Validators.required],
    mensagem: ['', Validators.required],
  });

  respostaTexto = '';
  // Controla localmente qual vista mostrar (lista ou conversa) — o
  // ticketAtual do store não é limpo ao voltar à lista (evitaria um
  // pedido extra se o utilizador reabrir o mesmo ticket), por isso não
  // dá para usar "ticketAtual$ tem valor?" sozinho para decidir a vista.
  ticketAbertoId: string | null = null;

  ngOnInit() {
    this.store.dispatch(SuporteActions.carregarMeusTickets({}));
    // UsuarioLogado (store/auth) não guarda o e-mail — só pré-preenche o
    // nome; o e-mail fica em branco para o Gestor confirmar.
    this.meuUsuario$.subscribe(usuario => {
      if (usuario) {
        this.ticketForm.patchValue({ nome: usuario.nome_completo }, { emitEvent: false });
      }
    });
  }

  alternarFormularioNovo() {
    this.mostrarFormularioNovo = !this.mostrarFormularioNovo;
  }

  onCriarTicket() {
    if (this.ticketForm.invalid) return;
    const { nome, email, assunto, mensagem } = this.ticketForm.getRawValue();
    this.store.dispatch(SuporteActions.criarTicket({ nome: nome!, email: email!, assunto: assunto!, mensagem: mensagem! }));
    this.mostrarFormularioNovo = false;
    this.ticketForm.patchValue({ assunto: '', mensagem: '' });
  }

  onAbrirTicket(id: string) {
    this.ticketAbertoId = id;
    this.store.dispatch(SuporteActions.carregarTicket({ id }));
  }

  onFecharTicket() {
    this.ticketAbertoId = null;
    this.store.dispatch(SuporteActions.carregarMeusTickets({}));
  }

  onEnviarResposta(id: string) {
    if (!this.respostaTexto.trim()) return;
    this.store.dispatch(SuporteActions.enviarMensagemTicket({ id, corpo: this.respostaTexto }));
    this.respostaTexto = '';
  }

  onPagina(pagina: number) {
    this.store.dispatch(SuporteActions.carregarMeusTickets({ page: pagina }));
  }

  onTamanho(tamanho: number) {
    this.store.dispatch(SuporteActions.carregarMeusTickets({ page: 1, page_size: tamanho }));
  }
}
