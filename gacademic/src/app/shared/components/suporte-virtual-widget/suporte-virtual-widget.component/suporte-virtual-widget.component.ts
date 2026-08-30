import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

interface MensagemChat {
  papel: 'visitante' | 'assistente';
  texto: string;
}

/**
 * Widget flutuante do Suporte Virtual (assistente de IA da
 * plataforma) — montado uma única vez na raiz da app (ver app.html),
 * por isso fica disponível tanto no site público como dentro da app
 * autenticada, sem duplicar em cada layout.
 *
 * Estado local (signals), sem NgRx: mesma filosofia do Prof. Virtual
 * (app/core/prof_virtual.py) — conversa sem persistência, viaja
 * inteira em cada pedido; um F5 perde o histórico.
 */
@Component({
  // Sem ".component" no seletor, ao contrário do resto da app: este é o
  // único componente instanciado como tag literal noutro template
  // (app.html) em vez de carregado pelo Router — um ponto no nome da
  // tag não é reconhecido pelo parser de templates do Angular fora
  // desse caso (confirmado ao testar: "not a known element").
  selector: 'app-suporte-virtual-widget',
  imports: [FormsModule, RouterLink],
  templateUrl: './suporte-virtual-widget.component.html',
  styleUrl: './suporte-virtual-widget.component.css',
})
export class SuporteVirtualWidgetComponent {
  private http = inject(HttpClient);

  aberto = signal(false);
  mensagens = signal<MensagemChat[]>([]);
  aProcessar = signal(false);
  erro = signal<string | null>(null);
  perguntaAtual = '';

  alternar() {
    this.aberto.update(v => !v);
  }

  onEnviarPergunta() {
    const pergunta = this.perguntaAtual.trim();
    if (!pergunta || this.aProcessar()) return;

    const historico = this.mensagens();
    this.mensagens.set([...historico, { papel: 'visitante', texto: pergunta }]);
    this.perguntaAtual = '';
    this.aProcessar.set(true);
    this.erro.set(null);

    this.http.post<{ resposta: string }>('/api/v1/public/suporte-virtual/perguntar', {
      historico, pergunta
    }).subscribe({
      next: (resp) => {
        this.mensagens.update(msgs => [...msgs, { papel: 'assistente', texto: resp.resposta }]);
        this.aProcessar.set(false);
      },
      error: (err) => {
        this.erro.set(err.error?.detail || 'Não foi possível responder agora. Tente novamente ou use a página de Contacto.');
        this.aProcessar.set(false);
      }
    });
  }
}
