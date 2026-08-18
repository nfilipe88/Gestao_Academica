import { Component, ElementRef, HostListener, inject, ViewChild } from '@angular/core';
import { PopoverCoordenadorService } from './popover-coordenador.service';

// Popover genérico e reutilizável: projeta um gatilho (dropdown) — o que
// abre/fecha — e um painel flutuante (popover) — o conteúdo, posicionado
// junto ao gatilho via position:fixed (segue o viewport, não fica preso
// pelo overflow-x-auto de contentores como a tabela do Mapa de
// Permissões, que é o primeiro sítio a usar isto).
//
// Uso:
//   <app-popover>
//     <button popoverGatilho>Abrir</button>
//     <div popoverConteudo>...</div>
//   </app-popover>
@Component({
  selector: 'app-popover',
  imports: [],
  templateUrl: './popover.component.html',
  styleUrl: './popover.component.css',
})
export class PopoverComponent {
  @ViewChild('gatilhoRef') gatilhoRef!: ElementRef<HTMLDivElement>;
  private coordenador = inject(PopoverCoordenadorService);

  aberto = false;
  posicao = { top: 0, left: 0 };

  alternar(event: MouseEvent) {
    event.stopPropagation();
    this.aberto ? this.fechar() : this.abrir();
  }

  abrir() {
    const rect = this.gatilhoRef.nativeElement.getBoundingClientRect();
    // Alinha à esquerda do gatilho por omissão; se não houver espaço à
    // direita (painel a sair do ecrã), alinha à direita do gatilho.
    const larguraEstimadaPainel = 180;
    const direita = rect.left + larguraEstimadaPainel > window.innerWidth;
    this.posicao = {
      top: rect.bottom + 4,
      left: direita ? rect.right - larguraEstimadaPainel : rect.left,
    };
    this.aberto = true;
    // Fecha qualquer outro popover aberto — o stopPropagation() acima
    // impede que isso aconteça sozinho via document:click (ver
    // PopoverCoordenadorService).
    this.coordenador.registar(this);
  }

  fechar() {
    this.aberto = false;
    this.coordenador.desregistar(this);
  }

  // Clique dentro do painel não deve fechar (checkboxes, etc.) —
  // qualquer outro clique no documento fecha.
  onConteudoClick(event: MouseEvent) {
    event.stopPropagation();
  }

  @HostListener('document:click')
  onDocumentClick() {
    if (this.aberto) this.fechar();
  }

  @HostListener('document:keydown.escape')
  onEscape() {
    if (this.aberto) this.fechar();
  }
}
