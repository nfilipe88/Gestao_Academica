import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { Store } from '@ngrx/store';
import { atualizarStatusTenant, carregarTenants } from '../../../store/admin/admin.actions';
import { selectAdminError, selectAdminMensagem, selectTenants } from '../../../store/admin/admin.selector';
import { StatusTenant } from '../../../store/admin/admin.models';

@Component({
  selector: 'app-admin.component',
  imports: [CommonModule, AsyncPipe],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css',
})
export class AdminComponent implements OnInit {
  private store = inject(Store);

  tenants$ = this.store.select(selectTenants);
  erro$ = this.store.select(selectAdminError);
  mensagem$ = this.store.select(selectAdminMensagem);

  // Qual tenant está a pedir confirmação inline ("Confirmar"/"Cancelar"
  // em vez do botão normal) — mesmo padrão dos restantes módulos, sem
  // depender de window.confirm() (não intercetável em automação/testes
  // e destoa do resto da UI, que nunca usa diálogos nativos).
  tenantAConfirmarId: string | null = null;

  ngOnInit() {
    this.store.dispatch(carregarTenants());
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
}
