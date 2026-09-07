import { Component, HostBinding, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { EventoPublico } from '../../../models/site-publico.models';
import { SitePublicoGalleryComponent } from '../../site-publico-gallery/site-publico-gallery.component/site-publico-gallery.component';

/**
 * Secção "Últimos Eventos" da página pública da escola — mesmo padrão
 * de componente "burro" de site-publico-gallery.component (recebe os
 * dados já prontos, `tema` só controla o CSS via [data-tema]),
 * inserida nos 4 templates logo a seguir à galeria (ver
 * templates/*.component.html).
 */
@Component({
  selector: 'app-site-publico-eventos',
  imports: [CommonModule, SitePublicoGalleryComponent],
  templateUrl: './site-publico-eventos.component.html',
  styleUrl: './site-publico-eventos.component.css',
})
export class SitePublicoEventosComponent {
  @Input({ required: true }) eventos!: EventoPublico[];
  @Input() tema: 'classico' | 'moderno' | 'acolhedor' | 'editorial' = 'classico';

  @HostBinding('attr.data-tema') get temaAttr() { return this.tema; }
}
