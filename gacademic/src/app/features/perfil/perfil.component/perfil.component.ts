import { AsyncPipe } from '@angular/common';
import { Component, inject, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import * as PerfilActions from '../../../store/perfil/perfil.actions';
import { selectPerfil, selectPerfilErro, selectPerfilMensagem } from '../../../store/perfil/perfil.selector';

@Component({
  selector: 'app-perfil.component',
  imports: [ReactiveFormsModule, AsyncPipe],
  templateUrl: './perfil.component.html',
  styleUrl: './perfil.component.css',
})
export class PerfilComponent implements OnInit, OnDestroy {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  perfil$ = this.store.select(selectPerfil);
  mensagem$ = this.store.select(selectPerfilMensagem);
  erro$ = this.store.select(selectPerfilErro);

  dadosForm = this.fb.group({
    nome_completo: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
  });

  senhaForm = this.fb.group({
    senha_atual: ['', Validators.required],
    nova_senha: ['', [Validators.required, Validators.minLength(8)]],
    confirmar_senha: ['', Validators.required],
  });

  ngOnInit() {
    this.store.dispatch(PerfilActions.limparMensagensPerfil());
    this.store.dispatch(PerfilActions.carregarPerfil());
    // Subscrição contínua (não take(1)): reage também ao próprio
    // carregarPerfilSucesso disparado depois de "Guardar", para o
    // formulário refletir exatamente o que ficou persistido — mesmo
    // padrão já usado em Configurações.
    this.perfil$.subscribe(perfil => {
      if (perfil) {
        this.dadosForm.patchValue({
          nome_completo: perfil.nome_completo,
          email: perfil.email,
        }, { emitEvent: false });
      }
    });
  }

  ngOnDestroy() {
    this.store.dispatch(PerfilActions.limparMensagensPerfil());
  }

  onGuardarDados() {
    if (this.dadosForm.invalid) return;
    const v = this.dadosForm.value;
    this.store.dispatch(PerfilActions.atualizarPerfil({ nome_completo: v.nome_completo!, email: v.email! }));
  }

  get senhasDiferentes(): boolean {
    const { nova_senha, confirmar_senha } = this.senhaForm.value;
    return !!nova_senha && !!confirmar_senha && nova_senha !== confirmar_senha;
  }

  onAlterarSenha() {
    if (this.senhaForm.invalid || this.senhasDiferentes) return;
    const v = this.senhaForm.value;
    this.store.dispatch(PerfilActions.alterarSenha({ senha_atual: v.senha_atual!, nova_senha: v.nova_senha! }));
    this.senhaForm.reset();
  }
}
