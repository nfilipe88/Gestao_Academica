import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import { carregarTenants } from '../../../store/admin/admin.actions';
import { selectTenants } from '../../../store/admin/admin.selector';
import { EstatisticasComponent } from '../../estatisticas/estatisticas.component/estatisticas.component';

// Envelope fino à volta do EstatisticasComponent normal (Gestor/
// Secretaria) — reaproveita-o por inteiro (dashboard, relatório por
// período, exports .xlsx/.xls, painel de Despesas) via [tenantId],
// só acrescenta o seletor de escola em cima. Ver
// features/estatisticas/estatisticas.component::@Input() tenantId e
// app/api/v1/admin.py (rotas /admin/tenants/{tenant_id}/estatisticas
// e /despesas, cross-tenant, só SUPER_ADMIN).
@Component({
  selector: 'app-estatisticas-admin.component',
  imports: [CommonModule, AsyncPipe, FormsModule, EstatisticasComponent],
  templateUrl: './estatisticas.component.html',
  styleUrl: './estatisticas.component.css',
})
export class EstatisticasAdminComponent implements OnInit {
  private store = inject(Store);

  // Mesma lista de Instituições do Painel Super Admin — um único
  // pedido com page_size alto chega para um <select> (não há
  // paginação aqui, ao contrário da tabela de /admin).
  tenants$ = this.store.select(selectTenants);

  tenantIdSelecionado: string | null = null;

  ngOnInit() {
    // 100 é o page_size máximo aceite pela API (Query(..., le=100) em
    // app/api/v1/admin.py) — chega para um <select> sem paginação; se a
    // plataforma vier a ter mais de 100 escolas, isto passa a precisar
    // de um campo de pesquisa em vez de listar tudo de uma vez.
    this.store.dispatch(carregarTenants({ page: 1, page_size: 100 }));
  }

  onEscolherEscola(tenantId: string) {
    this.tenantIdSelecionado = tenantId || null;
  }
}
