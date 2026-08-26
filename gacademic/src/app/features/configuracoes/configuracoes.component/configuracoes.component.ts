import { AsyncPipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import * as ConfiguracoesActions from '../../../store/configuracoes/configuracoes.actions';
import {
  selectConfiguracao, selectConfiguracoesError, selectConfiguracoesMensagem, selectTiposAvaliacao
} from '../../../store/configuracoes/configuracoes.selector';
import { MOEDAS_SUPORTADAS, TipoAvaliacao } from '../../../store/configuracoes/configuracoes.models';
import { selectIsGestor } from '../../../store/auth/auth.selectors';

@Component({
  selector: 'app-configuracoes.component',
  imports: [ReactiveFormsModule, AsyncPipe],
  templateUrl: './configuracoes.component.html',
  styleUrl: './configuracoes.component.css',
})
export class ConfiguracoesComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  readonly moedasSuportadas = MOEDAS_SUPORTADAS;

  // A leitura (GET /configuracoes) está aberta a qualquer utilizador
  // autenticado — a moeda é precisa em toda a plataforma, incluindo o
  // Portal. A escrita é GESTOR only no back-end; aqui escondemos o
  // formulário para quem não é Gestor, em vez de mostrar um botão
  // "Guardar" que pareceria funcionar e falharia só ao submeter.
  podeEditar$ = this.store.select(selectIsGestor);

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

  ngOnInit() {
    this.store.dispatch(ConfiguracoesActions.carregarConfiguracao());
    this.store.dispatch(ConfiguracoesActions.carregarTiposAvaliacao());
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
