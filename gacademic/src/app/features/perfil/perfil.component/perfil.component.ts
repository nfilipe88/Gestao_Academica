import { AsyncPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import * as PerfilActions from '../../../store/perfil/perfil.actions';
import { selectPerfil, selectPerfilErro, selectPerfilMensagem } from '../../../store/perfil/perfil.selector';
import { CapturaAssinaturaComponent } from '../../../shared/components/captura-assinatura/captura-assinatura.component/captura-assinatura.component';

// Perfis que efetivamente assinam documentos (ver app/core/assinaturas.py)
// — a secção de assinatura pessoal fica escondida para ALUNO/RESPONSAVEL,
// que podem tecnicamente enviar uma (o backend é permissivo de propósito,
// ver docstring de app/cruds/perfil.py) mas nunca teria efeito nenhum.
const PERFIS_COM_ASSINATURA_PESSOAL = ['GESTOR', 'SECRETARIA', 'PROFESSOR'];

@Component({
  selector: 'app-perfil.component',
  imports: [ReactiveFormsModule, AsyncPipe, CapturaAssinaturaComponent],
  templateUrl: './perfil.component.html',
  styleUrl: './perfil.component.css',
})
export class PerfilComponent implements OnInit, OnDestroy {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private http = inject(HttpClient);

  perfil$ = this.store.select(selectPerfil);
  mensagem$ = this.store.select(selectPerfilMensagem);
  erro$ = this.store.select(selectPerfilErro);

  // Mesmo raciocínio de signal() já usado em configuracoes.component.ts
  // (app zoneless — uma mutação dentro de .subscribe() de uma chamada
  // HTTP não é rastreada sozinha).
  assinaturaPessoalPreviewUrl = signal<string | null>(null);
  assinaturaPessoalAEnviar = signal(false);
  private assinaturaPessoalCarregada = false;

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

        if (perfil.tem_assinatura_pessoal !== this.assinaturaPessoalCarregada) {
          this.assinaturaPessoalCarregada = perfil.tem_assinatura_pessoal;
          if (perfil.tem_assinatura_pessoal) {
            this._carregarPreviewAssinaturaPessoal();
          } else {
            this._limparPreviewAssinaturaPessoal();
          }
        }
      }
    });
  }

  ngOnDestroy() {
    this.store.dispatch(PerfilActions.limparMensagensPerfil());
  }

  protected podeTerAssinaturaPessoal(perfilAcesso: string): boolean {
    return PERFIS_COM_ASSINATURA_PESSOAL.includes(perfilAcesso);
  }

  private _carregarPreviewAssinaturaPessoal() {
    this.http.get<{ url: string }>('/api/v1/perfil/assinatura').subscribe({
      next: (resp) => this.assinaturaPessoalPreviewUrl.set(resp.url),
      error: () => this.assinaturaPessoalPreviewUrl.set(null),
    });
  }

  private _limparPreviewAssinaturaPessoal() {
    this.assinaturaPessoalPreviewUrl.set(null);
  }

  onAssinaturaPessoalPronta(ficheiro: File) {
    const dados = new FormData();
    dados.append('ficheiro', ficheiro);
    this.assinaturaPessoalAEnviar.set(true);
    this.http.post('/api/v1/perfil/assinatura', dados).subscribe({
      next: () => {
        this.assinaturaPessoalAEnviar.set(false);
        this.assinaturaPessoalCarregada = true;
        this._carregarPreviewAssinaturaPessoal();
        this.store.dispatch(PerfilActions.carregarPerfil());
      },
      error: () => this.assinaturaPessoalAEnviar.set(false),
    });
  }

  onRemoverAssinaturaPessoal() {
    this.http.delete('/api/v1/perfil/assinatura').subscribe({
      next: () => {
        this.assinaturaPessoalCarregada = false;
        this._limparPreviewAssinaturaPessoal();
        this.store.dispatch(PerfilActions.carregarPerfil());
      },
    });
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
