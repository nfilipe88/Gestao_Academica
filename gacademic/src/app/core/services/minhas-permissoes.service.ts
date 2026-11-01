import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { OperacoesCrud } from '../../store/permissoes/permissoes.models';

interface MinhasPermissoes {
  // null = o mapa não restringe esta pessoa (equipa da plataforma).
  modulos: Record<string, OperacoesCrud> | null;
  perfil_personalizado: string | null;
}

/**
 * O que vale para quem tem a sessão, módulo a módulo (mapa base, restrições
 * da escola e perfil da escola) — só para o menu esconder o que a pessoa não
 * pode usar. Quem decide é sempre o back-end, em cada pedido (ver
 * back_end/app/core/mapa_permissoes.py). Carregado pelo DashboardLayout.
 */
@Injectable({ providedIn: 'root' })
export class MinhasPermissoesService {
  private http = inject(HttpClient);

  private readonly modulos = signal<Record<string, OperacoesCrud> | null>(null);
  readonly perfilPersonalizado = signal<string | null>(null);

  carregar(): void {
    this.modulos.set(null);
    this.perfilPersonalizado.set(null);
    this.http.get<MinhasPermissoes>('/api/v1/permissoes/minhas').subscribe({
      next: (r) => { this.modulos.set(r.modulos); this.perfilPersonalizado.set(r.perfil_personalizado); },
      error: () => { /* sem resposta, o menu mostra tudo e o back-end decide */ },
    });
  }

  /** Mostrar a entrada do menu deste módulo? Na dúvida (ainda a carregar, módulo fora do mapa), sim. */
  podeVer(modulo: string): boolean {
    const modulos = this.modulos();
    return !modulos || !(modulo in modulos) || modulos[modulo].pode_ler;
  }
}
