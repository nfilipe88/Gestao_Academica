import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { SitePublico } from '../../../site-publico.model';
import { linkWhatsapp } from '../../../site-publico.util';

/**
 * Modelo "Acolhedor" — suave e ilustrativo: tons pastel, formas
 * arredondadas, tom próximo. Pensado para infantário/ensino básico,
 * onde a mensagem para os pais é confiança e carinho, não prestígio
 * académico. Ver ../../../escola.component/escola.component.ts para
 * o contentor.
 */
@Component({
  selector: 'app-template-acolhedor',
  imports: [ReactiveFormsModule],
  templateUrl: './template-acolhedor.component.html',
  styleUrl: './template-acolhedor.component.css',
})
export class TemplateAcolhedorComponent {
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
