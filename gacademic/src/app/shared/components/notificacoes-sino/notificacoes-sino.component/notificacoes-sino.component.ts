import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, ElementRef, HostListener, inject, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Store } from '@ngrx/store';
import * as NotificacoesActions from '../../../../store/notificacoes/notificacoes.actions';
import { selectNotificacoes, selectTotalNaoLidas } from '../../../../store/notificacoes/notificacoes.selector';
import { Notificacao } from '../../../../store/notificacoes/notificacoes.models';

@Component({
  selector: 'app-notificacoes-sino',
  imports: [AsyncPipe, DatePipe],
  templateUrl: './notificacoes-sino.component.html',
  styleUrl: './notificacoes-sino.component.css',
})
export class NotificacoesSinoComponent implements OnInit {
  private store = inject(Store);
  private router = inject(Router);
  private elementRef = inject(ElementRef);

  notificacoes$ = this.store.select(selectNotificacoes);
  totalNaoLidas$ = this.store.select(selectTotalNaoLidas);

  painelAberto = false;

  ngOnInit(): void {
    // Contagem: dispara já e depois faz polling (ver NotificacoesEffects).
    // Lista: só carregada quando o painel é aberto pela primeira vez.
    this.store.dispatch(NotificacoesActions.carregarContagem());
  }

  alternarPainel(): void {
    this.painelAberto = !this.painelAberto;
    if (this.painelAberto) {
      this.store.dispatch(NotificacoesActions.carregarNotificacoes());
    }
  }

  // Fecha o painel ao clicar fora do componente.
  @HostListener('document:click', ['$event'])
  aoClicarFora(evento: MouseEvent): void {
    if (this.painelAberto && !this.elementRef.nativeElement.contains(evento.target)) {
      this.painelAberto = false;
    }
  }

  abrirNotificacao(notificacao: Notificacao): void {
    if (!notificacao.lida) {
      this.store.dispatch(NotificacoesActions.marcarComoLida({ id: notificacao.id }));
    }
    this.painelAberto = false;
    if (notificacao.link) {
      this.router.navigateByUrl(notificacao.link);
    }
  }

  marcarTodasComoLidas(evento: MouseEvent): void {
    evento.stopPropagation();
    this.store.dispatch(NotificacoesActions.marcarTodasComoLidas());
  }
}
