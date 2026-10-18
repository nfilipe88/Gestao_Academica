import { AsyncPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import * as PerfilActions from '../../../store/perfil/perfil.actions';
import { selectPerfil, selectPerfilErro, selectPerfilMensagem } from '../../../store/perfil/perfil.selector';
import { Perfil } from '../../../store/perfil/perfil.models';
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

  // Verificação em dois passos (código por e-mail no login). Mesmo
  // padrão HttpClient + signal() da assinatura pessoal acima.
  doisFatoresAtivo = signal(false);
  doisFatoresPasso = signal<'parado' | 'senha' | 'codigo'>('parado');
  doisFatoresEmail = signal('');
  doisFatoresErro = signal<string | null>(null);
  doisFatoresAEnviar = signal(false);
  private doisFatoresDesafio = '';
  doisFatoresForm = this.fb.group({
    senha_atual: [''],
    codigo: [''],
  });

  dadosForm = this.fb.group({
    nome_completo: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    // Só pedida (e enviada) quando o email muda — ver emailAlterado.
    senha_atual: [''],
  });

  // Email tal como está gravado — para saber se o formulário o mudou.
  private emailGravado = '';

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
        this.emailGravado = perfil.email;
        this.doisFatoresAtivo.set(perfil.dois_fatores_ativo);
        this.dadosForm.patchValue({
          nome_completo: perfil.nome_completo,
          email: perfil.email,
          senha_atual: '',
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

  // O email é o login e o destino da recuperação de palavra-passe — o
  // back-end exige a palavra-passe atual para o mudar (ver
  // app/cruds/perfil.py::atualizar_perfil).
  get emailAlterado(): boolean {
    return (this.dadosForm.value.email ?? '').trim() !== this.emailGravado;
  }

  onGuardarDados() {
    if (this.dadosForm.invalid) return;
    const v = this.dadosForm.value;
    if (this.emailAlterado && !v.senha_atual) return;
    this.store.dispatch(PerfilActions.atualizarPerfil({
      nome_completo: v.nome_completo!, email: v.email!,
      ...(this.emailAlterado ? { senha_atual: v.senha_atual! } : {}),
    }));
  }

  onIniciarDoisFatores() {
    this.doisFatoresErro.set(null);
    this.doisFatoresForm.reset();
    this.doisFatoresPasso.set('senha');
  }

  onCancelarDoisFatores() {
    this.doisFatoresErro.set(null);
    this.doisFatoresForm.reset();
    this.doisFatoresPasso.set('parado');
  }

  // Ligar: palavra-passe → código enviado por e-mail → confirmar o código.
  // Desligar: só a palavra-passe.
  onConfirmarSenhaDoisFatores() {
    const senha_atual = this.doisFatoresForm.value.senha_atual;
    if (!senha_atual) return;
    this.doisFatoresErro.set(null);
    this.doisFatoresAEnviar.set(true);
    if (this.doisFatoresAtivo()) {
      this.http.post<Perfil>('/api/v1/perfil/dois-fatores/desativar', { senha_atual }).subscribe({
        next: (perfil) => this._concluirDoisFatores(perfil, 'Verificação em dois passos desativada.'),
        error: (err) => this._falhaDoisFatores(err),
      });
      return;
    }
    this.http.post<{ desafio: string; email_mascarado: string }>('/api/v1/perfil/dois-fatores/ativar', { senha_atual }).subscribe({
      next: (res) => {
        this.doisFatoresAEnviar.set(false);
        this.doisFatoresDesafio = res.desafio;
        this.doisFatoresEmail.set(res.email_mascarado);
        this.doisFatoresForm.reset();
        this.doisFatoresPasso.set('codigo');
      },
      error: (err) => this._falhaDoisFatores(err),
    });
  }

  onConfirmarCodigoDoisFatores() {
    const codigo = (this.doisFatoresForm.value.codigo ?? '').trim();
    if (!/^\d{6}$/.test(codigo)) {
      this.doisFatoresErro.set('O código tem 6 dígitos.');
      return;
    }
    this.doisFatoresErro.set(null);
    this.doisFatoresAEnviar.set(true);
    this.http.post<Perfil>('/api/v1/perfil/dois-fatores/confirmar', { desafio: this.doisFatoresDesafio, codigo }).subscribe({
      next: (perfil) => this._concluirDoisFatores(perfil, 'Verificação em dois passos ativada.'),
      error: (err) => this._falhaDoisFatores(err),
    });
  }

  private _concluirDoisFatores(perfil: Perfil, mensagem: string) {
    this.doisFatoresAEnviar.set(false);
    this.doisFatoresPasso.set('parado');
    this.doisFatoresForm.reset();
    this.store.dispatch(PerfilActions.carregarPerfilSucesso({ perfil }));
    this.store.dispatch(PerfilActions.perfilOperacaoSucesso({ mensagem }));
  }

  private _falhaDoisFatores(err: { error?: { detail?: unknown } }) {
    this.doisFatoresAEnviar.set(false);
    const detail = err.error?.detail;
    this.doisFatoresErro.set(typeof detail === 'string' ? detail : 'Não foi possível concluir. Tente novamente.');
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
