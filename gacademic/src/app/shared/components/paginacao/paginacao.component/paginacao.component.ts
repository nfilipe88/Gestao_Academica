import { Component, EventEmitter, Input, Output } from '@angular/core';
import { EstadoPaginacao, TAMANHOS_PAGINA } from '../../../models/paginacao.models';

@Component({
  selector: 'app-paginacao',
  imports: [],
  templateUrl: './paginacao.component.html',
  styleUrl: './paginacao.component.css',
})
export class PaginacaoComponent {
  @Input({ required: true }) estado!: EstadoPaginacao;
  @Output() paginaChange = new EventEmitter<number>();
  @Output() tamanhoChange = new EventEmitter<number>();

  tamanhos = TAMANHOS_PAGINA;

  get inicio(): number {
    return this.estado.total === 0 ? 0 : (this.estado.page - 1) * this.estado.page_size + 1;
  }

  get fim(): number {
    return Math.min(this.estado.page * this.estado.page_size, this.estado.total);
  }

  onAnterior() {
    if (this.estado.page > 1) this.paginaChange.emit(this.estado.page - 1);
  }

  onSeguinte() {
    if (this.estado.page < this.estado.total_pages) this.paginaChange.emit(this.estado.page + 1);
  }

  onMudarTamanho(evento: Event) {
    const novoTamanho = Number((evento.target as HTMLSelectElement).value);
    this.tamanhoChange.emit(novoTamanho);
  }
}
