import { Injectable, signal } from '@angular/core';

export interface ToastItem {
  id: number;
  mensagem: string;
}

const DURACAO_MS = 8000;

/**
 * Rede de segurança global contra erros inesperados da API (500, falha de
 * rede) que nenhum effect concreto sabia mostrar — sem isto, um pedido que
 * falhe silenciosamente deixa o ecrã preso em "a carregar..." sem qualquer
 * pista para o utilizador (ver core/interceptors/erro-global.interceptor.ts,
 * que é quem chama mostrarErro).
 *
 * Não substitui as mensagens de erro específicas de cada módulo (inválidas,
 * de negócio, etc.) — essas continuam inline, mais úteis por saberem o
 * contexto. Este serviço só cobre o que mais ninguém tratou.
 */
@Injectable({ providedIn: 'root' })
export class ToastService {
  private contador = 0;
  readonly toasts = signal<ToastItem[]>([]);

  mostrarErro(mensagem: string): void {
    // Evita empilhar o mesmo aviso repetido quando vários pedidos em
    // paralelo falham ao mesmo tempo (ex.: o servidor cai a meio de um
    // ecrã com 5 chamadas simultâneas) — um só toast chega.
    if (this.toasts().some(t => t.mensagem === mensagem)) return;

    const id = ++this.contador;
    this.toasts.update(lista => [...lista, { id, mensagem }]);
    setTimeout(() => this.remover(id), DURACAO_MS);
  }

  remover(id: number): void {
    this.toasts.update(lista => lista.filter(t => t.id !== id));
  }
}
