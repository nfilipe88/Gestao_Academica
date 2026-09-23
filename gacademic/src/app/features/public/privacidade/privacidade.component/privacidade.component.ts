import { Component } from '@angular/core';

/**
 * Política de Privacidade e Retenção de Dados — texto de
 * POLITICA_PRIVACIDADE_RASCUNHO.md (Parte B), servido numa página pública.
 * Enquanto emRevisao for true, a página mostra um aviso bem visível de que
 * o texto é um rascunho ainda não em vigor e os campos por preencher
 * aparecem destacados — nunca apresentar como definitivo algo que o
 * jurista ainda não aprovou.
 *
 * Ao publicar: pôr emRevisao = false, preencher os campos destacados e
 * alinhar VERSAO_TERMOS em back_end/app/core/privacidade.py.
 */
@Component({
  selector: 'app-privacidade',
  templateUrl: './privacidade.component.html',
})
export class PrivacidadeComponent {
  readonly emRevisao = true;
}
