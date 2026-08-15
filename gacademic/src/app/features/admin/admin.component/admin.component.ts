import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import { atualizarStatusTenant, carregarTenants } from '../../../store/admin/admin.actions';
import { selectAdminError, selectAdminMensagem, selectTenants } from '../../../store/admin/admin.selector';
import { StatusTenant } from '../../../store/admin/admin.models';
import * as TransferenciasActions from '../../../store/transferencias/transferencias.actions';
import {
  selectSolicitacoesTransferencia, selectTransferenciasError, selectTransferenciasMensagem
} from '../../../store/transferencias/transferencias.selector';

@Component({
  selector: 'app-admin.component',
  imports: [CommonModule, AsyncPipe, FormsModule],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css',
})
export class AdminComponent implements OnInit {
  private store = inject(Store);

  tenants$ = this.store.select(selectTenants);
  erro$ = this.store.select(selectAdminError);
  mensagem$ = this.store.select(selectAdminMensagem);

  solicitacoesTransferencia$ = this.store.select(selectSolicitacoesTransferencia);
  erroTransferencias$ = this.store.select(selectTransferenciasError);
  mensagemTransferencias$ = this.store.select(selectTransferenciasMensagem);

  // Qual tenant está a pedir confirmação inline ("Confirmar"/"Cancelar"
  // em vez do botão normal) — mesmo padrão dos restantes módulos, sem
  // depender de window.confirm() (não intercetável em automação/testes
  // e destoa do resto da UI, que nunca usa diálogos nativos).
  tenantAConfirmarId: string | null = null;

  // Rejeição de transferência: id do pedido com o campo de observações aberto.
  solicitacaoARejeitar: string | null = null;
  observacoesRejeicao = '';

  ngOnInit() {
    this.store.dispatch(carregarTenants());
    this.store.dispatch(TransferenciasActions.carregarSolicitacoesSuperAdmin());
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
}
