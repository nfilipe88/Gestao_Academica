import { DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, Input, OnChanges, inject, signal } from '@angular/core';
import { PaginacaoComponent } from '../paginacao/paginacao.component/paginacao.component';
import { EstadoPaginacao, PAGINACAO_INICIAL, PaginaResultado } from '../../models/paginacao.models';

// Alinhado com app/schemas/seguranca.py.
export interface EventoSeguranca {
  id: string;
  data_evento: string;
  tipo: string;
  gravidade: 'BAIXA' | 'MEDIA' | 'ALTA';
  ip: string;
  user_agent: string | null;
  email: string | null;
  metodo: string | null;
  caminho: string | null;
  detalhe: string | null;
  tenant_id: string | null;
  nome_escola: string | null;
}

export const ROTULOS_TIPO_EVENTO: Record<string, string> = {
  TOKEN_FORJADO: 'Sessão forjada',
  ACESSO_NEGADO: 'Acesso a área sem permissão',
  FICHEIRO_MALICIOSO: 'Ficheiro malicioso',
  FICHEIRO_RECUSADO: 'Ficheiro recusado',
  SONDAGEM: 'Endereço suspeito',
  LOGIN_FALHADO: 'Palavra-passe errada',
  FORCA_BRUTA: 'Tentativas de login em excesso',
  DOIS_FATORES_FALHADO: 'Código de verificação errado',
  RECAPTCHA_FALHADO: 'Verificação anti-robô falhada',
  IP_BLOQUEADO: 'Endereço IP bloqueado',
};

/**
 * Tabela de eventos de segurança (ver app/core/eventos_seguranca.py) —
 * partilhada pelo separador "Segurança" do Gestor (só a própria escola)
 * e pela página de Segurança do Super Admin (todas as escolas). Carrega
 * os dados sozinha a partir de `url`; `filtros` extra (escola, IP) vêm
 * de quem a usa.
 */
@Component({
  selector: 'app-eventos-seguranca',
  imports: [DatePipe, PaginacaoComponent],
  templateUrl: './eventos-seguranca.component.html',
})
export class EventosSegurancaComponent implements OnChanges {
  private http = inject(HttpClient);

  @Input({ required: true }) url!: string;
  @Input() mostrarEscola = false;
  @Input() filtros: Record<string, string> = {};

  eventos = signal<EventoSeguranca[]>([]);
  paginacao = signal<EstadoPaginacao>(PAGINACAO_INICIAL);
  gravidade = signal('');
  aCarregar = signal(false);
  erro = signal<string | null>(null);
  eventoAberto = signal<string | null>(null);

  rotulo(tipo: string): string {
    return ROTULOS_TIPO_EVENTO[tipo] ?? tipo;
  }

  ngOnChanges() {
    this.carregar(1);
  }

  carregar(page = this.paginacao().page, pageSize = this.paginacao().page_size) {
    const params: Record<string, string | number> = { page, page_size: pageSize };
    for (const [chave, valor] of Object.entries(this.filtros)) {
      if (valor) params[chave] = valor;
    }
    if (this.gravidade()) params['gravidade'] = this.gravidade();
    this.aCarregar.set(true);
    this.erro.set(null);
    this.http.get<PaginaResultado<EventoSeguranca>>(this.url, { params }).subscribe({
      next: (resp) => {
        this.eventos.set(resp.items);
        this.paginacao.set({ total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages });
        this.aCarregar.set(false);
      },
      error: (err) => {
        this.aCarregar.set(false);
        this.erro.set(err.error?.detail || 'Não foi possível carregar os eventos de segurança.');
      },
    });
  }

  onGravidade(valor: string) {
    this.gravidade.set(valor);
    this.carregar(1);
  }

  alternarDetalhe(id: string) {
    this.eventoAberto.set(this.eventoAberto() === id ? null : id);
  }
}
