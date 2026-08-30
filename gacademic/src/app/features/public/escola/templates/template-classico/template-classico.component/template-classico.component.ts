import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { SitePublico } from '../../../../../../shared/models/site-publico.models';
import { SitePublicoLeadFormComponent } from '../../../../../../shared/components/site-publico-lead-form/site-publico-lead-form.component/site-publico-lead-form.component';
import { SitePublicoSocialLinksComponent } from '../../../../../../shared/components/site-publico-social-links/site-publico-social-links.component/site-publico-social-links.component';
import { SitePublicoGalleryComponent } from '../../../../../../shared/components/site-publico-gallery/site-publico-gallery.component/site-publico-gallery.component';

/**
 * Modelo "Clássico" — sóbrio e institucional: hero em tom escuro,
 * navegação tradicional, cursos numa lista expansível. Pensado para
 * escolas de posicionamento tradicional (secundário, universitário).
 * Ver ../../../escola.component/escola.component.ts para o contentor
 * que fornece os @Input()s e trata a submissão do formulário — o
 * formulário de contacto, as redes sociais e a galeria em si vivem em
 * shared/components/site-publico-*, partilhados pelos 4 modelos.
 */
@Component({
  selector: 'app-template-classico',
  imports: [SitePublicoLeadFormComponent, SitePublicoSocialLinksComponent, SitePublicoGalleryComponent],
  templateUrl: './template-classico.component.html',
  styleUrl: './template-classico.component.css',
})
export class TemplateClassicoComponent {
  @Input({ required: true }) escola!: SitePublico;
  @Input({ required: true }) leadForm!: FormGroup;
  @Input() leadEnviado = false;
  @Input() erroLead: string | null = null;
  @Output() submitLead = new EventEmitter<void>();

  // Só um curso expandido de cada vez — mesmo padrão usado em Cursos
  // (features/academico/cursos), aqui puramente de apresentação.
  cursoExpandidoId = signal<string | null>(null);
  alternarCurso(id: string) {
    this.cursoExpandidoId.set(this.cursoExpandidoId() === id ? null : id);
  }
}
