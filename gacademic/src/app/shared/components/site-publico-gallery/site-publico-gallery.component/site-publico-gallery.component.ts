import { Component, HostBinding, Input } from '@angular/core';

/**
 * Grelha de fotos da página pública da escola — mesma grelha 2/3
 * colunas nos 4 modelos, só o tratamento de cada foto muda (cantos,
 * moldura, preto-e-branco no Editorial) via `data-tema` (ver o .css).
 */
@Component({
  selector: 'app-site-publico-gallery',
  imports: [],
  templateUrl: './site-publico-gallery.component.html',
  styleUrl: './site-publico-gallery.component.css',
})
export class SitePublicoGalleryComponent {
  @Input({ required: true }) fotos!: string[];
  @Input() tema: 'classico' | 'moderno' | 'acolhedor' | 'editorial' = 'classico';

  @HostBinding('attr.data-tema') get temaAttr() { return this.tema; }
}
