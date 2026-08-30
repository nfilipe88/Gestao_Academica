import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { SitePublico } from '../../../site-publico.model';
import { linkWhatsapp } from '../../../site-publico.util';

/**
 * Modelo "Clássico" — sóbrio e institucional: hero em tom escuro,
 * navegação tradicional, cursos numa lista expansível. Pensado para
 * escolas de posicionamento tradicional (secundário, universitário).
 * Ver ../../../escola.component/escola.component.ts para o contentor
 * que fornece os @Input()s e trata a submissão do formulário.
 */
@Component({
  selector: 'app-template-classico',
  imports: [ReactiveFormsModule],
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

  readonly linkWhatsapp = linkWhatsapp;
}
