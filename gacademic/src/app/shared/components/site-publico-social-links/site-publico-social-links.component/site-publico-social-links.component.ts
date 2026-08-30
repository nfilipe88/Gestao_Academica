import { Component, HostBinding, Input } from '@angular/core';
import { linkWhatsapp } from '../../../../core/utils/site-publico-utils';

/**
 * Linha de redes sociais (Facebook/Instagram/WhatsApp) da página
 * pública da escola — mesma lógica nos 4 modelos (mostra só o que
 * está preenchido, WhatsApp com mensagem pré-feita), aspeto por tema
 * via `data-tema` (ver o .css). Ver site-publico-lead-form.component
 * para o mesmo raciocínio aplicado ao formulário de contacto.
 */
@Component({
  selector: 'app-site-publico-social-links',
  imports: [],
  templateUrl: './site-publico-social-links.component.html',
  styleUrl: './site-publico-social-links.component.css',
})
export class SitePublicoSocialLinksComponent {
  @Input() facebook: string | null = null;
  @Input() instagram: string | null = null;
  @Input() whatsapp: string | null = null;
  @Input({ required: true }) nomeEscola!: string;
  @Input() tema: 'classico' | 'moderno' | 'acolhedor' | 'editorial' = 'classico';

  @HostBinding('attr.data-tema') get temaAttr() { return this.tema; }

  get linkWhatsapp(): string {
    return this.whatsapp ? linkWhatsapp(this.whatsapp, this.nomeEscola) : '';
  }
}
