import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { OperacoesCrud } from '../../store/permissoes/permissoes.models';

interface MinhasPermissoes {
  // null = o mapa não restringe esta pessoa (equipa da plataforma).
  modulos: Record<string, OperacoesCrud> | null;
  perfil_personalizado: string | null;
  // {módulo: [o que ele precisa de ler e esta pessoa não pode]}.
  leituras_em_falta: Record<string, string[]>;
}

// Módulo do Mapa de Permissões de cada página (a mesma partição do menu).
const MODULO_DA_ROTA: Record<string, string> = {
  '/indicadores': 'Indicadores', '/estatisticas': 'Estatísticas', '/cursos': 'Cursos',
  '/turmas': 'Turmas & Matrículas', '/rematricula': 'Turmas & Matrículas', '/fecho-ano': 'Turmas & Matrículas',
  '/alunos': 'Alunos & Responsáveis', '/calendario': 'Configurações', '/diario': 'Diário de Classe',
  '/importacao': 'Diário de Classe', '/tarefas': 'Trabalhos / Tarefas', '/horarios': 'Horários',
  '/crm': 'CRM', '/transferencias': 'Transferências de Alunos', '/financeiro': 'Financeiro',
  '/propinas': 'Financeiro', '/comunicacoes': 'Comunicações', '/documentos': 'Documentos (interno)',
  '/professores': 'Professores', '/configuracoes': 'Configurações', '/eventos': 'Configurações',
};

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
  private readonly leiturasEmFalta = signal<Record<string, string[]>>({});

  carregar(): void {
    this.modulos.set(null);
    this.perfilPersonalizado.set(null);
    this.leiturasEmFalta.set({});
    this.http.get<MinhasPermissoes>('/api/v1/permissoes/minhas').subscribe({
      next: (r) => {
        this.modulos.set(r.modulos);
        this.perfilPersonalizado.set(r.perfil_personalizado);
        this.leiturasEmFalta.set(r.leituras_em_falta ?? {});
      },
      error: () => { /* sem resposta, o menu mostra tudo e o back-end decide */ },
    });
  }

  /** Mostrar a entrada do menu deste módulo? Na dúvida (ainda a carregar, módulo fora do mapa), sim. */
  podeVer(modulo: string): boolean {
    const modulos = this.modulos();
    return !modulos || !(modulo in modulos) || modulos[modulo].pode_ler;
  }

  podeVerAlgum(...modulos: string[]): boolean {
    return modulos.some(m => this.podeVer(m));
  }

  /** Mostrar uma ligação para esta página? (rotas fora do mapa: sim) */
  podeVerRota(rota: string): boolean {
    const modulo = MODULO_DA_ROTA[rota.split(/[?#]/)[0]];
    return !modulo || this.podeVer(modulo);
  }

  /** O que esta página precisa de ler e esta pessoa não pode — para explicar porque fica vazia. */
  leiturasEmFaltaDaRota(rota: string): string[] {
    const modulo = MODULO_DA_ROTA[rota.split(/[?#]/)[0]];
    return (modulo && this.leiturasEmFalta()[modulo]) || [];
  }
}
