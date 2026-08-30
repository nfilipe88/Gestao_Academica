import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Meta, Title } from '@angular/platform-browser';
import { ActivatedRoute } from '@angular/router';
import { SitePublico } from '../../../../shared/models/site-publico.models';
import { TemplateClassicoComponent } from '../templates/template-classico/template-classico.component/template-classico.component';
import { TemplateModernoComponent } from '../templates/template-moderno/template-moderno.component/template-moderno.component';
import { TemplateAcolhedorComponent } from '../templates/template-acolhedor/template-acolhedor.component/template-acolhedor.component';
import { TemplateEditorialComponent } from '../templates/template-editorial/template-editorial.component/template-editorial.component';

/**
 * Página pública de apresentação de UMA escola cliente (marketing/
 * angariação de alunos) — distinta do site público da PLATAFORMA
 * (features/public/landing/...): aqui é a escola que se apresenta a
 * famílias, com a marca dela (logótipo, nome), não a nossa. Por isso
 * fica FORA de PublicLayoutComponent (sem o nav/rodapé "SaaS
 * Académico") — mesmo raciocínio de captar-lead.component, que também
 * é uma página standalone por pertencer à escola, não à plataforma.
 *
 * Este componente é só o CONTENTOR: busca os dados, é dono do
 * formulário de contacto/lead (RN03 do CRM) e das meta tags — a
 * apresentação em si fica nos 4 modelos visuais (./templates/*),
 * escolhidos pela escola em Configurações (SitePublico.template).
 * Cada modelo recebe os mesmos dados/estado e só decide COMO os
 * desenha, nunca duplica a lógica de submissão do formulário.
 */
@Component({
  selector: 'app-escola.component',
  imports: [ReactiveFormsModule, TemplateClassicoComponent, TemplateModernoComponent, TemplateAcolhedorComponent, TemplateEditorialComponent],
  templateUrl: './escola.component.html',
  styleUrl: './escola.component.css',
})
export class EscolaComponent implements OnInit {
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private fb = inject(FormBuilder);
  private titleService = inject(Title);
  private meta = inject(Meta);

  identificador = this.route.snapshot.paramMap.get('tenantId') ?? '';

  escola = signal<SitePublico | null>(null);
  aCarregar = signal(true);
  naoEncontrada = signal(false);

  leadEnviado = signal(false);
  erroLead = signal<string | null>(null);
  leadForm = this.fb.group({
    nome_responsavel: ['', Validators.required],
    email_contato: ['', Validators.email],
    telefone: [''],
    nome_aluno_candidato: ['', Validators.required],
    origem_lead: ['SITE'],
  });

  ngOnInit() {
    if (!this.identificador) { this.naoEncontrada.set(true); this.aCarregar.set(false); return; }
    this.http.get<SitePublico>(`/api/v1/public/escola/${this.identificador}`).subscribe({
      next: (escola) => { this.escola.set(escola); this.aCarregar.set(false); this._definirMetaTags(escola); },
      error: () => { this.naoEncontrada.set(true); this.aCarregar.set(false); },
    });
  }

  // Título e meta tags Open Graph — para a página aparecer bem quando
  // partilhada no WhatsApp/Facebook e com um título decente no Google,
  // em vez de ficar sempre com o <title> genérico "Gacademic" de
  // index.html (ver app.html/index.html).
  private _definirMetaTags(escola: SitePublico) {
    this.titleService.setTitle(escola.nome_fantasia);
    const descricao = (escola.missao || `Conheça ${escola.nome_fantasia}.`).slice(0, 160);
    this.meta.updateTag({ name: 'description', content: descricao });
    this.meta.updateTag({ property: 'og:title', content: escola.nome_fantasia });
    this.meta.updateTag({ property: 'og:description', content: descricao });
    this.meta.updateTag({ property: 'og:type', content: 'website' });
    if (escola.logotipo) this.meta.updateTag({ property: 'og:image', content: escola.logotipo });
  }

  onSubmitLead() {
    // O endpoint de leads (RN03 do CRM) só aceita o uuid do tenant, ao
    // contrário do endpoint da página em si — que já aceita slug ou
    // uuid (ver ngOnInit). Por isso vai sempre pelo tenant_id devolvido
    // na resposta, nunca por this.identificador (o segmento da URL, que
    // pode ser o slug quando a página foi aberta por /escola/<slug>).
    const tenantId = this.escola()?.tenant_id;
    if (this.leadForm.invalid || !tenantId) return;
    this.erroLead.set(null);
    this.http.post(`/api/v1/public/${tenantId}/leads`, this.leadForm.value).subscribe({
      next: () => { this.leadEnviado.set(true); },
      error: (err) => {
        const detail = err.error?.detail;
        this.erroLead.set(typeof detail === 'string' ? detail : 'Não foi possível enviar o seu pedido. Tente novamente.');
      }
    });
  }
}
