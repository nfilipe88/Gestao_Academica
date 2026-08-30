import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';
import { SitePublico } from '../../../site-publico.model';
import { linkWhatsapp } from '../../../site-publico.util';

/**
 * Modelo "Editorial" — minimalista: preto e branco, muito espaço em
 * branco, tipografia grande, filetes finos, cursos como lista
 * numerada. Pensado para um posicionamento premium/exclusivo, onde a
 * discrição transmite mais confiança do que cor e ilustração. Ver
 * ../../../escola.component/escola.component.ts para o contentor.
 */
@Component({
  selector: 'app-template-editorial',
  imports: [ReactiveFormsModule],
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

  readonly linkWhatsapp = linkWhatsapp;

  numero(indice: number): string {
    return String(indice + 1).padStart(2, '0');
  }
}
