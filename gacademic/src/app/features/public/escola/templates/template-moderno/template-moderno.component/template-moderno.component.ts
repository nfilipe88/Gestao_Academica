import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { SitePublico } from '../../../site-publico.model';
import { linkWhatsapp } from '../../../site-publico.util';

/**
 * Modelo "Moderno" — vibrante e arrojado: hero em gradiente, cartões
 * arredondados, navegação em pílula flutuante. Pensado para escolas
 * de posicionamento jovem/tecnológico. Ver
 * ../../../escola.component/escola.component.ts para o contentor.
 */
@Component({
  selector: 'app-template-moderno',
  imports: [ReactiveFormsModule],
  templateUrl: './template-moderno.component.html',
  styleUrl: './template-moderno.component.css',
})
export class TemplateModernoComponent {
  @Input({ required: true }) escola!: SitePublico;
  @Input({ required: true }) leadForm!: FormGroup;
  @Input() leadEnviado = false;
  @Input() erroLead: string | null = null;
  @Output() submitLead = new EventEmitter<void>();

  cursoExpandidoId = signal<string | null>(null);
  alternarCurso(id: string) {
    this.cursoExpandidoId.set(this.cursoExpandidoId() === id ? null : id);
  }

  readonly linkWhatsapp = linkWhatsapp;
}
