import { Injectable } from '@angular/core';

// Garante que só um app-popover fica aberto de cada vez — sem isto, o
// clique num gatilho para abrir um popover B faz stopPropagation() (ver
// popover.component.ts::alternar, necessário para o próprio clique que
// abriu B não chegar ao document:click e fechá-lo de imediato), o que
// por efeito colateral também impede o document:click do popover A de
// disparar, deixando A e B abertos ao mesmo tempo. Em vez de depender
// do bubbling do evento, cada popover regista-se aqui ao abrir e o
// coordenador fecha diretamente o anterior.
@Injectable({ providedIn: 'root' })
export class PopoverCoordenadorService {
  private abertoAtual: { fechar: () => void } | null = null;

  registar(instancia: { fechar: () => void }) {
    if (this.abertoAtual && this.abertoAtual !== instancia) {
      this.abertoAtual.fechar();
    }
    this.abertoAtual = instancia;
  }

  desregistar(instancia: { fechar: () => void }) {
    if (this.abertoAtual === instancia) {
      this.abertoAtual = null;
    }
  }
}
