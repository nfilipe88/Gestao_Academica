import { AsyncPipe, DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import { carregarTenants } from '../../../store/admin/admin.actions';
import { selectTenants } from '../../../store/admin/admin.selector';
import { EventosSegurancaComponent } from '../../../shared/components/eventos-seguranca/eventos-seguranca.component';

interface BloqueioIp {
  ip: string;
  ate: string;
  motivo: string;
}

/**
 * Segurança da plataforma (Super Admin): tentativas de acesso indevido em
 * todas as escolas — incluindo as anónimas, sem escola (varrimentos,
 * sessões forjadas) — e os IPs bloqueados automaticamente, com a opção de
 * os desbloquear (ex.: era a rede de uma escola, não um ataque).
 * Ver app/core/eventos_seguranca.py e app/api/v1/admin.py.
 */
@Component({
  selector: 'app-seguranca-admin',
  imports: [AsyncPipe, DatePipe, FormsModule, EventosSegurancaComponent],
  templateUrl: './seguranca.component.html',
})
export class SegurancaAdminComponent implements OnInit {
  private store = inject(Store);
  private http = inject(HttpClient);

  tenants$ = this.store.select(selectTenants);

  tenantId = '';
  ip = '';
  // Objeto novo a cada mudança: é isso que faz a tabela recarregar (ngOnChanges).
  filtros = signal<Record<string, string>>({});

  bloqueios = signal<BloqueioIp[]>([]);
  mensagem = signal<string | null>(null);

  ngOnInit() {
    this.store.dispatch(carregarTenants({ page: 1, page_size: 100 }));
    this.carregarBloqueios();
  }

  aplicarFiltros() {
    this.filtros.set({ tenant_id: this.tenantId, ip: this.ip.trim() });
  }

  filtrarPorIp(ip: string) {
    this.ip = ip;
    this.aplicarFiltros();
  }

  carregarBloqueios() {
    this.http.get<BloqueioIp[]>('/api/v1/admin/seguranca/bloqueios').subscribe({
      next: (lista) => this.bloqueios.set(lista),
    });
  }

  desbloquear(ip: string) {
    this.http.delete<{ mensagem: string }>(`/api/v1/admin/seguranca/bloqueios/${encodeURIComponent(ip)}`).subscribe({
      next: (resp) => {
        this.mensagem.set(resp.mensagem);
        this.carregarBloqueios();
      },
    });
  }
}
