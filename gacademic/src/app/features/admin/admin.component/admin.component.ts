import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import {
  atualizarStatusTenant, atualizarValidadeLicenca, carregarTenants, criarTenant, processarValidadeLicencas,
  carregarPlanos, criarPlano, atualizarPlano, apagarPlano, carregarMrr,
  carregarAssinaturaTenant, definirAssinaturaTenant, cancelarAssinaturaTenant
} from '../../../store/admin/admin.actions';
import { selectAdminError, selectAdminMensagem, selectPaginacaoTenants, selectTenants } from '../../../store/admin/admin.selector';
import { selectPlanos, selectPlanosAtivos, selectMrr, selectAssinaturasPorTenant } from '../../../store/admin/admin.selector';
import { FiltrosTenants, PlanoSaaS, StatusTenant } from '../../../store/admin/admin.models';
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

  // Onboarding gatekeeping — Super Admin cria a escola diretamente, em
  // alternativa ao auto-serviço em /registo.
  mostrarFormularioNovaEscola = false;
  novaEscolaForm = this.fb.group({
    nome_fantasia: ['', Validators.required],
    nif: ['', Validators.required],
    nome_gestor: ['', Validators.required],
    email_gestor: ['', [Validators.required, Validators.email]],
    palavra_passe: ['', [Validators.required, Validators.minLength(8)]],
  });

  // Rejeição de transferência: id do pedido com o campo de observações aberto.
  solicitacaoARejeitar: string | null = null;
  observacoesRejeicao = '';

  paginaTenants = 1;
  tamanhoTenants = 25;
  paginaTransferencias = 1;
  tamanhoTransferencias = 25;

  // Filtro da tabela de Instituições: nome (com debounce, para não
  // disparar um pedido a cada tecla), plano e intervalo de nº de
  // utilizadores — mesmo padrão reativo já usado em Alunos/CRM/etc.
  filtroTenantsForm = this.fb.group({
    nome: [''],
    plano_id: [''],
    usuarios_min: [null as number | null],
    usuarios_max: [null as number | null],
  });

  // --- SaaS Billing: Planos, Assinaturas e MRR ---
  planos$ = this.store.select(selectPlanos);
  planosAtivos$ = this.store.select(selectPlanosAtivos);
  mrr$ = this.store.select(selectMrr);
  assinaturasPorTenant$ = this.store.select(selectAssinaturasPorTenant);

  mostrarFormularioPlano = false;
  planoAEditar: PlanoSaaS | null = null;
  planoForm = this.fb.group({
    nome: ['', Validators.required],
    preco_mensal: [0, [Validators.required, Validators.min(0)]],
    limite_alunos: [null as number | null],
    descricao: [''],
    dias_periodo_teste: [0, [Validators.required, Validators.min(0)]],
  });
  planoAApagarId: string | null = null;

  // Assinatura por escola — expandida sob um tenant de cada vez, mesmo
  // padrão da Gestão de Acessos.
  assinaturaDoTenantId: string | null = null;

  ngOnInit() {
    this.store.dispatch(carregarTenants({ page: this.paginaTenants, page_size: this.tamanhoTenants }));
    this.store.dispatch(TransferenciasActions.carregarSolicitacoesSuperAdmin({ page: this.paginaTransferencias, page_size: this.tamanhoTransferencias }));
    this.store.dispatch(carregarPlanos());
    this.store.dispatch(carregarMrr());

    this.filtroTenantsForm.controls.nome.valueChanges.pipe(
      debounceTime(300), distinctUntilChanged()
    ).subscribe(() => this.aplicarFiltrosTenants());
    this.filtroTenantsForm.controls.plano_id.valueChanges.subscribe(() => this.aplicarFiltrosTenants());
    this.filtroTenantsForm.controls.usuarios_min.valueChanges.subscribe(() => this.aplicarFiltrosTenants());
    this.filtroTenantsForm.controls.usuarios_max.valueChanges.subscribe(() => this.aplicarFiltrosTenants());
  }

  private filtrosTenantsAtuais(): FiltrosTenants {
    const v = this.filtroTenantsForm.value;
    return {
      nome: v.nome || undefined,
      plano_id: v.plano_id || undefined,
      usuarios_min: v.usuarios_min ?? undefined,
      usuarios_max: v.usuarios_max ?? undefined,
    };
  }

  private dispatchTenantsComFiltros(pagina: number) {
    this.store.dispatch(carregarTenants({ page: pagina, page_size: this.tamanhoTenants, filtros: this.filtrosTenantsAtuais() }));
  }

  aplicarFiltrosTenants() {
    this.paginaTenants = 1;
    this.dispatchTenantsComFiltros(1);
  }

  limparFiltrosTenants() {
    this.filtroTenantsForm.reset({ nome: '', plano_id: '', usuarios_min: null, usuarios_max: null });
    this.aplicarFiltrosTenants();
  }

  onPaginaTenants(pagina: number) {
    this.paginaTenants = pagina;
    this.dispatchTenantsComFiltros(pagina);
  }

  onTamanhoTenants(tamanho: number) {
    this.tamanhoTenants = tamanho;
    this.paginaTenants = 1;
    this.dispatchTenantsComFiltros(1);
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

  alternarFormularioNovaEscola() {
    this.mostrarFormularioNovaEscola = !this.mostrarFormularioNovaEscola;
    this.novaEscolaForm.reset({ nome_fantasia: '', nif: '', nome_gestor: '', email_gestor: '', palavra_passe: '' });
  }

  onCriarEscola() {
    if (this.novaEscolaForm.invalid) return;
    const v = this.novaEscolaForm.value;
    this.store.dispatch(criarTenant({
      nome_fantasia: v.nome_fantasia!, nif: v.nif!, nome_gestor: v.nome_gestor!,
      email_gestor: v.email_gestor!, palavra_passe: v.palavra_passe!
    }));
    this.mostrarFormularioNovaEscola = false;
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

  // --- SaaS Billing: Planos ---

  alternarFormularioPlano() {
    this.mostrarFormularioPlano = !this.mostrarFormularioPlano;
    this.planoAEditar = null;
    this.planoForm.reset({ nome: '', preco_mensal: 0, limite_alunos: null, descricao: '', dias_periodo_teste: 0 });
  }

  onEditarPlano(plano: PlanoSaaS) {
    this.planoAEditar = plano;
    this.mostrarFormularioPlano = true;
    this.planoForm.reset({
      nome: plano.nome, preco_mensal: plano.preco_mensal,
      limite_alunos: plano.limite_alunos, descricao: plano.descricao,
      dias_periodo_teste: plano.dias_periodo_teste,
    });
  }

  onGuardarPlano() {
    if (this.planoForm.invalid) return;
    const v = this.planoForm.value;
    if (this.planoAEditar) {
      this.store.dispatch(atualizarPlano({
        id: this.planoAEditar.id, nome: v.nome!, preco_mensal: v.preco_mensal!,
        limite_alunos: v.limite_alunos ?? null, descricao: v.descricao || null,
        dias_periodo_teste: v.dias_periodo_teste ?? 0, ativo: this.planoAEditar.ativo
      }));
    } else {
      this.store.dispatch(criarPlano({
        nome: v.nome!, preco_mensal: v.preco_mensal!,
        limite_alunos: v.limite_alunos ?? null, descricao: v.descricao || null,
        dias_periodo_teste: v.dias_periodo_teste ?? 0,
      }));
    }
    this.mostrarFormularioPlano = false;
    this.planoAEditar = null;
  }

  onAlternarAtivoPlano(plano: PlanoSaaS) {
    this.store.dispatch(atualizarPlano({
      id: plano.id, nome: plano.nome, preco_mensal: plano.preco_mensal,
      limite_alunos: plano.limite_alunos, descricao: plano.descricao,
      dias_periodo_teste: plano.dias_periodo_teste, ativo: !plano.ativo
    }));
  }

  onPedirApagarPlano(planoId: string) {
    this.planoAApagarId = planoId;
  }

  onCancelarApagarPlano() {
    this.planoAApagarId = null;
  }

  onConfirmarApagarPlano(planoId: string) {
    this.store.dispatch(apagarPlano({ id: planoId }));
    this.planoAApagarId = null;
  }

  // --- SaaS Billing: Assinatura por escola ---

  onAlternarAssinatura(tenantId: string) {
    this.assinaturaDoTenantId = this.assinaturaDoTenantId === tenantId ? null : tenantId;
    if (this.assinaturaDoTenantId) {
      this.store.dispatch(carregarAssinaturaTenant({ tenant_id: tenantId }));
    }
  }

  onDefinirAssinatura(tenantId: string, planoId: string, proximaCobranca: string) {
    if (!planoId || !proximaCobranca) return;
    this.store.dispatch(definirAssinaturaTenant({ tenant_id: tenantId, plano_id: planoId, proxima_cobranca: proximaCobranca }));
  }

  onCancelarAssinatura(tenantId: string) {
    this.store.dispatch(cancelarAssinaturaTenant({ tenant_id: tenantId }));
  }

  // Sugestão de data ao escolher o plano no formulário de assinatura:
  // se o plano tem período de teste, a primeira cobrança só faz
  // sentido no fim do teste; sem teste, sugere-se o mês seguinte. É só
  // uma sugestão pré-preenchida — o campo de data continua editável.
  sugerirProximaCobranca(planoId: string, planos: PlanoSaaS[] | null): string {
    const plano = planos?.find(p => p.id === planoId);
    const dias = plano?.dias_periodo_teste && plano.dias_periodo_teste > 0 ? plano.dias_periodo_teste : 30;
    const data = new Date();
    data.setDate(data.getDate() + dias);
    return data.toISOString().slice(0, 10);
  }
}
