import { Component, EventEmitter, HostBinding, Input, Output } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';

/**
 * Formulário de contacto/lead (RN03 do CRM) partilhado pelos 4
 * modelos de página pública (features/public/escola/templates/*) —
 * os campos e a validação são sempre os mesmos; só o aspeto muda.
 *
 * Em vez de 4 cópias quase idênticas do mesmo `<form>` (o que já
 * aconteceu — um novo campo tinha de ser lembrado 4 vezes), este
 * componente fica "burro": recebe o FormGroup e o estado já geridos
 * pelo contentor (escola.component.ts, dono da chamada à API) e só
 * decide como desenhar os campos. O aspeto de cada modelo vem do
 * atributo `data-tema` (ver site-publico-lead-form.component.css) —
 * tokens CSS (`--sp-*`) por tema, não classes Tailwind coladas em 4
 * sítios diferentes.
 */
@Component({
  selector: 'app-site-publico-lead-form',
  imports: [ReactiveFormsModule],
  templateUrl: './site-publico-lead-form.component.html',
  styleUrl: './site-publico-lead-form.component.css',
})
export class SitePublicoLeadFormComponent {
  @Input({ required: true }) form!: FormGroup;
  @Input() erro: string | null = null;
  @Input() tema: 'classico' | 'moderno' | 'acolhedor' | 'editorial' = 'classico';
  @Output() enviar = new EventEmitter<void>();

  @HostBinding('attr.data-tema') get temaAttr() { return this.tema; }
}
