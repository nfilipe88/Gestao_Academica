import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import * as UsuariosActions from '../../../store/usuarios/usuarios.actions';
import {
  selectPaginacaoAuditoria, selectPaginacaoUsuarios, selectUsuarios, selectUsuariosAuditoria,
  selectUsuariosError, selectUsuariosMensagem
} from '../../../store/usuarios/usuarios.selector';
import { PERFIS_ATRIBUIVEIS, UsuarioStaff } from '../../../store/usuarios/usuarios.models';
import { selectIsGestor, selectUsuario } from '../../../store/auth/auth.selectors';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';

@Component({
  selector: 'app-acessos.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe, PaginacaoComponent],
  templateUrl: './acessos.component.html',
  styleUrl: './acessos.component.css',
})
export class AcessosComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  usuarios$ = this.store.select(selectUsuarios);
  paginacaoUsuarios$ = this.store.select(selectPaginacaoUsuarios);
  auditoria$ = this.store.select(selectUsuariosAuditoria);
  paginacaoAuditoria$ = this.store.select(selectPaginacaoAuditoria);
  erro$ = this.store.select(selectUsuariosError);
  mensagem$ = this.store.select(selectUsuariosMensagem);
  meuUsuario$ = this.store.select(selectUsuario);
  // Leitura/escrita são GESTOR only no back-end (/api/v1/usuarios) —
  // esconde o conteúdo em vez de mostrar um ecrã que dá sempre 403,
  // mesmo padrão já usado em Configurações.
  podeAceder$ = this.store.select(selectIsGestor);

  perfisAtribuiveis = PERFIS_ATRIBUIVEIS;

  aba: 'staff' | 'auditoria' = 'staff';
  mostrarFormularioSecretaria = false;
  secretariaForm = this.fb.group({
    nome_completo: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    palavra_passe: ['', [Validators.required, Validators.minLength(8)]],
  });

  // Linha com o <select> de perfil aberto — evita mudar sem confirmar.
  usuarioAEditarPerfilId: string | null = null;
  usuarioASuspenderId: string | null = null;

  ngOnInit() {
    this.store.dispatch(UsuariosActions.carregarUsuarios({}));
  }

  onPaginaStaff(pagina: number) {
    this.store.dispatch(UsuariosActions.carregarUsuarios({ page: pagina }));
  }

  onTamanhoStaff(tamanho: number) {
    this.store.dispatch(UsuariosActions.carregarUsuarios({ page: 1, page_size: tamanho }));
  }

  alternarFormularioSecretaria() {
    this.mostrarFormularioSecretaria = !this.mostrarFormularioSecretaria;
    this.secretariaForm.reset({ nome_completo: '', email: '', palavra_passe: '' });
  }

  onCriarSecretaria() {
    if (this.secretariaForm.invalid) return;
    const v = this.secretariaForm.value;
    this.store.dispatch(UsuariosActions.criarSecretaria({ nome_completo: v.nome_completo!, email: v.email!, palavra_passe: v.palavra_passe! }));
    this.mostrarFormularioSecretaria = false;
  }

  onAbrirEdicaoPerfil(usuarioId: string) {
    this.usuarioAEditarPerfilId = usuarioId;
  }

  onCancelarEdicaoPerfil() {
    this.usuarioAEditarPerfilId = null;
  }

  onGuardarPerfil(usuarioId: string, novoPerfil: string) {
    if (novoPerfil !== 'GESTOR' && novoPerfil !== 'SECRETARIA') return;
    this.store.dispatch(UsuariosActions.alterarPerfil({ usuario_id: usuarioId, perfil_acesso: novoPerfil }));
    this.usuarioAEditarPerfilId = null;
  }

  onPedirSuspensao(usuarioId: string) {
    this.usuarioASuspenderId = usuarioId;
  }

  onCancelarSuspensao() {
    this.usuarioASuspenderId = null;
  }

  onConfirmarAlterarAtivo(usuarioId: string, ativo: boolean) {
    this.store.dispatch(UsuariosActions.alterarAtivo({ usuario_id: usuarioId, ativo }));
    this.usuarioASuspenderId = null;
  }

  // Perfil sem tabela satélite (Gestor/Secretaria) -> pode ser mudado
  // por aqui; Professor tem alocações/Diário associados (ver docstring
  // do crud) e mantém o fluxo próprio em Professores.
  podeMudarPerfil(usuario: UsuarioStaff): boolean {
    return usuario.perfil_acesso === 'GESTOR' || usuario.perfil_acesso === 'SECRETARIA';
  }

  onVerAuditoria() {
    this.aba = 'auditoria';
    this.store.dispatch(UsuariosActions.carregarAuditoria({}));
  }

  onPaginaAuditoria(pagina: number) {
    this.store.dispatch(UsuariosActions.carregarAuditoria({ page: pagina }));
  }

  onTamanhoAuditoria(tamanho: number) {
    this.store.dispatch(UsuariosActions.carregarAuditoria({ page: 1, page_size: tamanho }));
  }

  labelAcao(acao: string): string {
    const labels: Record<string, string> = {
      CRIACAO_SECRETARIA: 'Conta de Secretaria criada',
      MUDANCA_PERFIL: 'Mudança de perfil',
      SUSPENSAO: 'Acesso suspenso',
      REATIVACAO: 'Acesso reativado',
    };
    return labels[acao] ?? acao;
  }
}
