import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { atualizarStatusTenant, atualizarValidadeLicenca, carregarTenants, processarValidadeLicencas } from '../../../store/admin/admin.actions';
import { selectAdminError, selectAdminMensagem, selectPaginacaoTenants, selectTenants } from '../../../store/admin/admin.selector';
import { StatusTenant } from '../../../store/admin/admin.models';
import * as TransferenciasActions from '../../../store/transferencias/transferencias.actions';
import {
  selectPaginacaoTransferencias, selectSolicitacoesTransferencia, selectTransferenciasError, selectTransferenciasMensagem
} from '../../../store/transferencias/transferencias.selector';
import * as UsuariosActions from '../../../store/usuarios/usuarios.actions';
import { selectPaginacaoUsuarios, selectUsuarios, selectUsuariosError, selectUsuariosMensagem } from '../../../store/usuarios/usuarios.selector';
import { PERFIS_ATRIBUIVEIS, UsuarioStaff } from '../../../store/usuarios/usuarios.models';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';

@Component({
  selector: 'app-admin.component',
  imports: [CommonModule, AsyncPipe, FormsModule, ReactiveFormsModule, PaginacaoComponent],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css',
})
export class AdminComponent implements OnInit {
  private store = inject(Store);
  private fb = inject(FormBuilder);

  tenants$ = this.store.select(selectTenants);
  paginacaoTenants$ = this.store.select(selectPaginacaoTenants);
  erro$ = this.store.select(selectAdminError);
  mensagem$ = this.store.select(selectAdminMensagem);

  solicitacoesTransferencia$ = this.store.select(selectSolicitacoesTransferencia);
  paginacaoTransferencias$ = this.store.select(selectPaginacaoTransferencias);
  erroTransferencias$ = this.store.select(selectTransferenciasError);
  mensagemTransferencias$ = this.store.select(selectTransferenciasMensagem);

  // Gestão de Acessos por escola (expandida sob um tenant de cada vez —
  // mesma store partilhada com o Gestor, ver usuarios.effects.ts::baseUrl).
  usuariosDoTenantId: string | null = null;
  usuarios$ = this.store.select(selectUsuarios);
  paginacaoUsuarios$ = this.store.select(selectPaginacaoUsuarios);
  erroUsuarios$ = this.store.select(selectUsuariosError);
  mensagemUsuarios$ = this.store.select(selectUsuariosMensagem);
  perfisAtribuiveis = PERFIS_ATRIBUIVEIS;
  mostrarFormularioSecretaria = false;
  secretariaForm = this.fb.group({
    nome_completo: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    palavra_passe: ['', [Validators.required, Validators.minLength(8)]],
  });
  usuarioAEditarPerfilId: string | null = null;
  usuarioASuspenderId: string | null = null;

  // Qual tenant está a pedir confirmação inline ("Confirmar"/"Cancelar"
  // em vez do botão normal) — mesmo padrão dos restantes módulos, sem
  // depender de window.confirm() (não intercetável em automação/testes
  // e destoa do resto da UI, que nunca usa diálogos nativos).
  tenantAConfirmarId: string | null = null;

  // Rejeição de transferência: id do pedido com o campo de observações aberto.
  solicitacaoARejeitar: string | null = null;
  observacoesRejeicao = '';

  paginaTenants = 1;
  tamanhoTenants = 25;
  paginaTransferencias = 1;
  tamanhoTransferencias = 25;

  ngOnInit() {
    this.store.dispatch(carregarTenants({ page: this.paginaTenants, page_size: this.tamanhoTenants }));
    this.store.dispatch(TransferenciasActions.carregarSolicitacoesSuperAdmin({ page: this.paginaTransferencias, page_size: this.tamanhoTransferencias }));
  }

  onPaginaTenants(pagina: number) {
    this.paginaTenants = pagina;
    this.store.dispatch(carregarTenants({ page: pagina, page_size: this.tamanhoTenants }));
  }

  onTamanhoTenants(tamanho: number) {
    this.tamanhoTenants = tamanho;
    this.paginaTenants = 1;
    this.store.dispatch(carregarTenants({ page: 1, page_size: tamanho }));
  }

  onPaginaTransferencias(pagina: number) {
    this.paginaTransferencias = pagina;
    this.store.dispatch(TransferenciasActions.carregarSolicitacoesSuperAdmin({ page: pagina, page_size: this.tamanhoTransferencias }));
  }

  onTamanhoTransferencias(tamanho: number) {
    this.tamanhoTransferencias = tamanho;
    this.paginaTransferencias = 1;
    this.store.dispatch(TransferenciasActions.carregarSolicitacoesSuperAdmin({ page: 1, page_size: tamanho }));
  }

  pedirConfirmacao(tenantId: string) {
    this.tenantAConfirmarId = tenantId;
  }

  cancelarConfirmacao() {
    this.tenantAConfirmarId = null;
  }

  onAlternarStatus(tenantId: string, statusAtual: StatusTenant) {
    const novoStatus: StatusTenant = statusAtual === 'ATIVO' ? 'SUSPENSO' : 'ATIVO';
    this.store.dispatch(atualizarStatusTenant({ tenant_id: tenantId, status: novoStatus }));
    this.tenantAConfirmarId = null;
  }

  onGuardarValidadeLicenca(tenantId: string, dataValidade: string) {
    this.store.dispatch(atualizarValidadeLicenca({ tenant_id: tenantId, data_validade_licenca: dataValidade || null }));
  }

  onProcessarValidadeLicencas() {
    this.store.dispatch(processarValidadeLicencas());
  }

  // dias até expirar (negativo = já expirou); null se não houver data
  // definida. Envolvido num objeto (em vez de devolver o número
  // diretamente) porque o template usa "@if (...; as dias)", que testa
  // a expressão por truthiness — um resultado 0 (expira hoje) seria
  // tratado como "sem valor" e o aviso desaparecia exatamente no dia
  // em que mais importa mostrá-lo.
  diasAteExpirar(dataValidade: string | null): { dias: number } | null {
    if (!dataValidade) return null;
    const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
    const validade = new Date(dataValidade + 'T00:00:00');
    return { dias: Math.round((validade.getTime() - hoje.getTime()) / (1000 * 60 * 60 * 24)) };
  }

  onAprovarTransferencia(solicitacaoId: string) {
    this.store.dispatch(TransferenciasActions.aprovarSolicitacao({ solicitacao_id: solicitacaoId }));
  }

  onAbrirRejeicao(solicitacaoId: string) {
    this.solicitacaoARejeitar = solicitacaoId;
    this.observacoesRejeicao = '';
  }

  onConfirmarRejeicao(solicitacaoId: string) {
    if (!this.observacoesRejeicao.trim()) return;
    this.store.dispatch(TransferenciasActions.rejeitarSolicitacao({ solicitacao_id: solicitacaoId, observacoes: this.observacoesRejeicao }));
    this.solicitacaoARejeitar = null;
  }

  // --- Gestão de Acessos por escola (cross-tenant) ---

  onAlternarGestaoAcessos(tenantId: string) {
    this.usuariosDoTenantId = this.usuariosDoTenantId === tenantId ? null : tenantId;
    this.mostrarFormularioSecretaria = false;
    this.usuarioAEditarPerfilId = null;
    this.usuarioASuspenderId = null;
    if (this.usuariosDoTenantId) {
      this.store.dispatch(UsuariosActions.carregarUsuarios({ tenant_id: tenantId }));
    }
  }

  onPaginaUsuarios(pagina: number) {
    if (!this.usuariosDoTenantId) return;
    this.store.dispatch(UsuariosActions.carregarUsuarios({ tenant_id: this.usuariosDoTenantId, page: pagina }));
  }

  onTamanhoUsuarios(tamanho: number) {
    if (!this.usuariosDoTenantId) return;
    this.store.dispatch(UsuariosActions.carregarUsuarios({ tenant_id: this.usuariosDoTenantId, page: 1, page_size: tamanho }));
  }

  alternarFormularioSecretaria() {
    this.mostrarFormularioSecretaria = !this.mostrarFormularioSecretaria;
    this.secretariaForm.reset({ nome_completo: '', email: '', palavra_passe: '' });
  }

  onCriarSecretaria() {
    if (this.secretariaForm.invalid || !this.usuariosDoTenantId) return;
    const v = this.secretariaForm.value;
    this.store.dispatch(UsuariosActions.criarSecretaria({
      tenant_id: this.usuariosDoTenantId, nome_completo: v.nome_completo!, email: v.email!, palavra_passe: v.palavra_passe!
    }));
    this.mostrarFormularioSecretaria = false;
  }

  onAbrirEdicaoPerfil(usuarioId: string) {
    this.usuarioAEditarPerfilId = usuarioId;
  }

  onCancelarEdicaoPerfil() {
    this.usuarioAEditarPerfilId = null;
  }

  onGuardarPerfil(usuarioId: string, novoPerfil: string) {
    if ((novoPerfil !== 'GESTOR' && novoPerfil !== 'SECRETARIA') || !this.usuariosDoTenantId) return;
    this.store.dispatch(UsuariosActions.alterarPerfil({ tenant_id: this.usuariosDoTenantId, usuario_id: usuarioId, perfil_acesso: novoPerfil }));
    this.usuarioAEditarPerfilId = null;
  }

  onPedirSuspensaoUsuario(usuarioId: string) {
    this.usuarioASuspenderId = usuarioId;
  }

  onCancelarSuspensaoUsuario() {
    this.usuarioASuspenderId = null;
  }

  onConfirmarAlterarAtivo(usuarioId: string, ativo: boolean) {
    if (!this.usuariosDoTenantId) return;
    this.store.dispatch(UsuariosActions.alterarAtivo({ tenant_id: this.usuariosDoTenantId, usuario_id: usuarioId, ativo }));
    this.usuarioASuspenderId = null;
  }

  podeMudarPerfil(usuario: UsuarioStaff): boolean {
    return usuario.perfil_acesso === 'GESTOR' || usuario.perfil_acesso === 'SECRETARIA';
  }
}
