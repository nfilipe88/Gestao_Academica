import { AsyncPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import * as ConfiguracoesActions from '../../../store/configuracoes/configuracoes.actions';
import {
  selectConfiguracao, selectConfiguracoesError, selectConfiguracoesMensagem, selectTiposAvaliacao
} from '../../../store/configuracoes/configuracoes.selector';
import { MOEDAS_SUPORTADAS, TipoAvaliacao } from '../../../store/configuracoes/configuracoes.models';
import { selectIsGestor, selectTenantId } from '../../../store/auth/auth.selectors';

interface SitePublicoFoto {
  id: string;
  url: string;
}

interface SitePublicoConfig {
  ativo: boolean;
  slug: string | null;
  missao: string | null;
  metodologia: string | null;
  facebook: string | null;
  instagram: string | null;
  whatsapp: string | null;
  fotos: SitePublicoFoto[];
}

@Component({
  selector: 'app-configuracoes.component',
  imports: [ReactiveFormsModule, AsyncPipe, RouterLink],
  templateUrl: './configuracoes.component.html',
  styleUrl: './configuracoes.component.css',
})
export class ConfiguracoesComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private http = inject(HttpClient);

  readonly moedasSuportadas = MOEDAS_SUPORTADAS;

  // A leitura (GET /configuracoes) está aberta a qualquer utilizador
  // autenticado — a moeda é precisa em toda a plataforma, incluindo o
  // Portal. A escrita é GESTOR only no back-end; aqui escondemos o
  // formulário para quem não é Gestor, em vez de mostrar um botão
  // "Guardar" que pareceria funcionar e falharia só ao submeter.
  podeEditar$ = this.store.select(selectIsGestor);
  tenantId$ = this.store.select(selectTenantId);

  mensagem$ = this.store.select(selectConfiguracoesMensagem);
  erro$ = this.store.select(selectConfiguracoesError);
  tiposAvaliacao$ = this.store.select(selectTiposAvaliacao);

  form = this.fb.group({
    iban: [''],
    moeda: ['EUR', Validators.required],
    telefone_contacto: [''],
    email_contacto: ['', Validators.email],
    morada: [''],
    cidade: [''],
    codigo_postal: [''],
    pais: [''],
    nota_minima_aprovacao: [''],
    periodo_manha_inicio: [''],
    periodo_manha_fim: [''],
    periodo_tarde_inicio: [''],
    periodo_tarde_fim: [''],
    periodo_pos_laboral_inicio: [''],
    periodo_pos_laboral_fim: [''],
  });

  // Formulário separado, mais simples, para criar um novo tipo de
  // avaliação — mantido fora do form principal porque não faz parte de
  // ConfiguracaoTenant (é outra entidade, TipoAvaliacaoConfig).
  novoTipoForm = this.fb.group({
    nome: ['', Validators.required],
    requer_agendamento: [false],
  });
  mostrarFormularioNovoTipo = false;
  edicaoTipoId: string | null = null;
  edicaoTipoForm = this.fb.group({
    nome: ['', Validators.required],
    requer_agendamento: [false],
    ativo: [true],
  });

  // GET /configuracoes/logotipo exige o cabeçalho Authorization, por
  // isso não pode ser um <img src="/api/..."> direto — vai por
  // HttpClient como blob, e o resultado vira um object URL local.
  //
  // signal() e não uma propriedade simples: esta app é zoneless (sem
  // zone.js — ver app.config.ts/main.ts), e uma mutação feita dentro
  // de um callback .subscribe() de uma chamada HTTP não passa por
  // nenhum mecanismo que o Angular já rastreie sozinho (nem escrita de
  // signal, nem template binding, nem async pipe) — a vista ficava
  // presa no valor antigo apesar da propriedade estar correta.
  logotipoPreviewUrl = signal<string | null>(null);
  logotipoAEnviar = signal(false);
  private logotipoCarregado = false;

  // ==========================================
  // SITE PÚBLICO DA ESCOLA (marketing/angariação de alunos)
  // ==========================================
  // Mesmo raciocínio de signal() do logótipo acima: chega por
  // HttpClient direto (não pelo store de configuracoes), fora de
  // qualquer mecanismo que o Angular já rastreie sozinho neste app zoneless.
  sitePublico = signal<SitePublicoConfig | null>(null);
  sitePublicoForm = this.fb.group({
    ativo: [false],
    slug: ['', [Validators.pattern(/^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$/), Validators.minLength(3), Validators.maxLength(80)]],
    missao: [''],
    metodologia: [''],
    facebook: [''],
    instagram: [''],
    whatsapp: [''],
  });
  fotoAEnviar = signal(false);
  erroSitePublico = signal<string | null>(null);
  mensagemSitePublico = signal<string | null>(null);

  ngOnInit() {
    this.store.dispatch(ConfiguracoesActions.carregarConfiguracao());
    this.store.dispatch(ConfiguracoesActions.carregarTiposAvaliacao());
    this._carregarSitePublico();
    // Subscrição contínua (não take(1)): também reage ao próprio
    // carregarConfiguracaoSucesso disparado depois de "Guardar", para o
    // formulário refletir exatamente o que ficou persistido (ex.: a
    // moeda normalizada para maiúsculas pelo back-end). Seguro porque
    // nada mais nesta app volta a despachar carregarConfiguracao depois
    // do arranque do ecrã (dashboard-layout só o faz uma vez, ao entrar).
    this.store.select(selectConfiguracao).subscribe(config => {
      this.form.patchValue({
        iban: config.iban ?? '',
        moeda: config.moeda || 'EUR',
        telefone_contacto: config.telefone_contacto ?? '',
        email_contacto: config.email_contacto ?? '',
        morada: config.morada ?? '',
        cidade: config.cidade ?? '',
        codigo_postal: config.codigo_postal ?? '',
        pais: config.pais ?? '',
        nota_minima_aprovacao: config.nota_minima_aprovacao != null ? String(config.nota_minima_aprovacao) : '',
        periodo_manha_inicio: config.periodo_manha_inicio ?? '',
        periodo_manha_fim: config.periodo_manha_fim ?? '',
        periodo_tarde_inicio: config.periodo_tarde_inicio ?? '',
        periodo_tarde_fim: config.periodo_tarde_fim ?? '',
        periodo_pos_laboral_inicio: config.periodo_pos_laboral_inicio ?? '',
        periodo_pos_laboral_fim: config.periodo_pos_laboral_fim ?? '',
      }, { emitEvent: false });

      // Só busca a imagem quando o estado "tem_logotipo" muda por uma
      // via que não seja já ter sido tratada diretamente (ver
      // onSelecionarLogotipo/onRemoverLogotipo, que atualizam
      // logotipoCarregado e o preview logo ali, sem esperar por esta
      // subscrição) — evita um pedido a mais a cada emissão do store,
      // mas continua a cobrir o carregamento inicial da página.
      if (config.tem_logotipo !== this.logotipoCarregado) {
        this.logotipoCarregado = config.tem_logotipo;
        if (config.tem_logotipo) {
          this._carregarPreviewLogotipo();
        } else {
          this._limparPreviewLogotipo();
        }
      }
    });
  }

  private _carregarPreviewLogotipo() {
    this.http.get('/api/v1/configuracoes/logotipo', { responseType: 'blob' }).subscribe({
      next: (blob) => {
        this._limparPreviewLogotipo();
        this.logotipoPreviewUrl.set(URL.createObjectURL(blob));
      },
      error: () => { this.logotipoPreviewUrl.set(null); },
    });
  }

  private _limparPreviewLogotipo() {
    const atual = this.logotipoPreviewUrl();
    if (atual) URL.revokeObjectURL(atual);
    this.logotipoPreviewUrl.set(null);
  }

  onSelecionarLogotipo(event: Event) {
    const ficheiro = (event.target as HTMLInputElement).files?.[0];
    if (!ficheiro) return;
    const dados = new FormData();
    dados.append('ficheiro', ficheiro);
    this.logotipoAEnviar.set(true);
    this.http.put('/api/v1/configuracoes/logotipo', dados).subscribe({
      next: () => {
        this.logotipoAEnviar.set(false);
        // Trata o preview já aqui (não pelo efeito da subscrição acima):
        // ao SUBSTITUIR um logótipo já existente, "tem_logotipo" continua
        // true antes e depois — o efeito, que só reage a MUDANÇAS desse
        // booleano, nunca disparava, e a pré-visualização ficava presa
        // na imagem antiga.
        this.logotipoCarregado = true;
        this._carregarPreviewLogotipo();
        this.store.dispatch(ConfiguracoesActions.carregarConfiguracao());
      },
      error: () => { this.logotipoAEnviar.set(false); },
    });
    (event.target as HTMLInputElement).value = ''; // permite voltar a escolher o mesmo ficheiro depois
  }

  onRemoverLogotipo() {
    this.http.delete('/api/v1/configuracoes/logotipo').subscribe({
      next: () => {
        this.logotipoCarregado = false;
        this._limparPreviewLogotipo();
        this.store.dispatch(ConfiguracoesActions.carregarConfiguracao());
      },
    });
  }

  private _carregarSitePublico() {
    this.http.get<SitePublicoConfig>('/api/v1/configuracoes/site-publico').subscribe({
      next: (config) => {
        this.sitePublico.set(config);
        this.sitePublicoForm.patchValue({
          ativo: config.ativo, slug: config.slug ?? '', missao: config.missao ?? '', metodologia: config.metodologia ?? '',
          facebook: config.facebook ?? '', instagram: config.instagram ?? '', whatsapp: config.whatsapp ?? '',
        }, { emitEvent: false });
      },
    });
  }

  onGuardarSitePublico() {
    if (this.sitePublicoForm.invalid) return;
    const v = this.sitePublicoForm.getRawValue();
    this.erroSitePublico.set(null);
    this.mensagemSitePublico.set(null);
    this.http.put<SitePublicoConfig>('/api/v1/configuracoes/site-publico', {
      ativo: !!v.ativo, slug: v.slug || null, missao: v.missao || null, metodologia: v.metodologia || null,
      facebook: v.facebook || null, instagram: v.instagram || null, whatsapp: v.whatsapp || null,
    }).subscribe({
      next: (config) => {
        this.sitePublico.set(config);
        this.sitePublicoForm.patchValue({ slug: config.slug ?? '' }, { emitEvent: false });
        this.mensagemSitePublico.set('Site público atualizado.');
      },
      error: (err) => this.erroSitePublico.set(err.error?.detail || 'Não foi possível guardar o site público.'),
    });
  }

  /** Identificador a usar no link a divulgar — o slug legível quando já
   * escolhido, senão o uuid do tenant (a página continua acessível por
   * ele, só menos apresentável). */
  linkSitePublico(tenantId: string): string {
    return this.sitePublico()?.slug || tenantId;
  }

  onSelecionarFoto(event: Event) {
    const ficheiro = (event.target as HTMLInputElement).files?.[0];
    if (!ficheiro) return;
    const dados = new FormData();
    dados.append('ficheiro', ficheiro);
    this.fotoAEnviar.set(true);
    this.erroSitePublico.set(null);
    this.http.post<SitePublicoConfig>('/api/v1/configuracoes/site-publico/fotos', dados).subscribe({
      next: (config) => { this.fotoAEnviar.set(false); this.sitePublico.set(config); },
      error: (err) => { this.fotoAEnviar.set(false); this.erroSitePublico.set(err.error?.detail || 'Não foi possível enviar a foto.'); },
    });
    (event.target as HTMLInputElement).value = '';
  }

  onRemoverFoto(fotoId: string) {
    this.http.delete<SitePublicoConfig>(`/api/v1/configuracoes/site-publico/fotos/${fotoId}`).subscribe({
      next: (config) => this.sitePublico.set(config),
    });
  }

  onGuardar() {
    if (this.form.invalid) return;
    const v = this.form.value;
    this.store.dispatch(ConfiguracoesActions.atualizarConfiguracao({
      dados: {
        iban: v.iban || null,
        moeda: v.moeda!,
        telefone_contacto: v.telefone_contacto || null,
        email_contacto: v.email_contacto || null,
        morada: v.morada || null,
        cidade: v.cidade || null,
        codigo_postal: v.codigo_postal || null,
        pais: v.pais || null,
        nota_minima_aprovacao: v.nota_minima_aprovacao ? Number(v.nota_minima_aprovacao) : null,
        periodo_manha_inicio: v.periodo_manha_inicio || null,
        periodo_manha_fim: v.periodo_manha_fim || null,
        periodo_tarde_inicio: v.periodo_tarde_inicio || null,
        periodo_tarde_fim: v.periodo_tarde_fim || null,
        periodo_pos_laboral_inicio: v.periodo_pos_laboral_inicio || null,
        periodo_pos_laboral_fim: v.periodo_pos_laboral_fim || null,
      }
    }));
  }

  // ==========================================
  // TIPOS DE AVALIAÇÃO
  // ==========================================
  alternarFormularioNovoTipo() {
    this.mostrarFormularioNovoTipo = !this.mostrarFormularioNovoTipo;
    this.novoTipoForm.reset({ nome: '', requer_agendamento: false });
  }

  onCriarTipo() {
    if (this.novoTipoForm.invalid) return;
    const v = this.novoTipoForm.value;
    this.store.dispatch(ConfiguracoesActions.criarTipoAvaliacao({ nome: v.nome!, requer_agendamento: !!v.requer_agendamento }));
    this.mostrarFormularioNovoTipo = false;
  }

  onEditarTipo(tipo: TipoAvaliacao) {
    this.edicaoTipoId = tipo.id;
    this.edicaoTipoForm.setValue({ nome: tipo.nome, requer_agendamento: tipo.requer_agendamento, ativo: tipo.ativo });
  }

  onCancelarEdicaoTipo() {
    this.edicaoTipoId = null;
  }

  onGuardarEdicaoTipo() {
    if (this.edicaoTipoForm.invalid || !this.edicaoTipoId) return;
    const v = this.edicaoTipoForm.value;
    this.store.dispatch(ConfiguracoesActions.atualizarTipoAvaliacao({
      id: this.edicaoTipoId, nome: v.nome!, requer_agendamento: !!v.requer_agendamento, ativo: !!v.ativo
    }));
    this.edicaoTipoId = null;
  }

  onAlternarAtivo(tipo: TipoAvaliacao) {
    this.store.dispatch(ConfiguracoesActions.atualizarTipoAvaliacao({
      id: tipo.id, nome: tipo.nome, requer_agendamento: tipo.requer_agendamento, ativo: !tipo.ativo
    }));
  }
}
