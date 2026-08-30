import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { SitePublico } from '../../../../../../shared/models/site-publico.models';
import { SitePublicoLeadFormComponent } from '../../../../../../shared/components/site-publico-lead-form/site-publico-lead-form.component/site-publico-lead-form.component';
import { SitePublicoSocialLinksComponent } from '../../../../../../shared/components/site-publico-social-links/site-publico-social-links.component/site-publico-social-links.component';
import { SitePublicoGalleryComponent } from '../../../../../../shared/components/site-publico-gallery/site-publico-gallery.component/site-publico-gallery.component';

/**
 * Modelo "Editorial" — minimalista: preto e branco, muito espaço em
 * branco, tipografia grande, filetes finos, cursos como lista
 * numerada. Pensado para um posicionamento premium/exclusivo, onde a
 * discrição transmite mais confiança do que cor e ilustração. Ver
 * ../../../escola.component/escola.component.ts para o contentor.
 */
@Component({
  selector: 'app-template-editorial',
  imports: [RouterLink, SitePublicoLeadFormComponent, SitePublicoSocialLinksComponent, SitePublicoGalleryComponent],
  templateUrl: './template-editorial.component.html',
  styleUrl: './template-editorial.component.css',
})
export class TemplateEditorialComponent {
  @Input({ required: true }) escola!: SitePublico;
  @Input({ required: true }) leadForm!: FormGroup;
  @Input() leadEnviado = false;
  @Input() erroLead: string | null = null;
  @Output() submitLead = new EventEmitter<void>();

  cursoExpandidoId = signal<string | null>(null);
  alternarCurso(id: string) {
    this.cursoExpandidoId.set(this.cursoExpandidoId() === id ? null : id);
  }

  numero(indice: number): string {
    return String(indice + 1).padStart(2, '0');
  }
}
