import { AsyncPipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import * as ConfiguracoesActions from '../../../store/configuracoes/configuracoes.actions';
import { selectConfiguracao, selectConfiguracoesError, selectConfiguracoesMensagem } from '../../../store/configuracoes/configuracoes.selector';
import { MOEDAS_SUPORTADAS } from '../../../store/configuracoes/configuracoes.models';
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

  form = this.fb.group({
    iban: [''],
    moeda: ['EUR', Validators.required],
    telefone_contacto: [''],
    email_contacto: ['', Validators.email],
    morada: [''],
    cidade: [''],
    codigo_postal: [''],
    pais: [''],
  });

  ngOnInit() {
    this.store.dispatch(ConfiguracoesActions.carregarConfiguracao());
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
      }
    }));
  }
}
