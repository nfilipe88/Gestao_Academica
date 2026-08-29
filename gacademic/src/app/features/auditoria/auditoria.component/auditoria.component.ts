import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import * as AuditoriaActions from '../../../store/auditoria/auditoria.actions';
import {
  selectAuditoriaEntidades, selectAuditoriaErro, selectAuditoriaPaginacao, selectAuditoriaRegistos
} from '../../../store/auditoria/auditoria.selector';
import { AcaoAuditoria, AlteracaoCampo, AuditLogRegisto } from '../../../store/auditoria/auditoria.models';
import { selectIsGestor } from '../../../store/auth/auth.selectors';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';

const ROTULOS_ACAO: Record<AcaoAuditoria, string> = {
  CRIADO: 'Criado', ALTERADO: 'Alterado', APAGADO: 'Apagado',
};

@Component({
  selector: 'app-auditoria.component',
  imports: [AsyncPipe, DatePipe, FormsModule, PaginacaoComponent],
  templateUrl: './auditoria.component.html',
  styleUrl: './auditoria.component.css',
})
export class AuditoriaComponent implements OnInit {
  private store = inject(Store);

  registos$ = this.store.select(selectAuditoriaRegistos);
  paginacao$ = this.store.select(selectAuditoriaPaginacao);
  entidades$ = this.store.select(selectAuditoriaEntidades);
  erro$ = this.store.select(selectAuditoriaErro);
  // Leitura é GESTOR only no back-end (/api/v1/auditoria) — esconde o
  // conteúdo em vez de mostrar um ecrã que dá sempre 403, mesmo padrão
  // já usado em Configurações e Gestão de Acessos.
  podeAceder$ = this.store.select(selectIsGestor);

  readonly acoes: AcaoAuditoria[] = ['CRIADO', 'ALTERADO', 'APAGADO'];
  readonly rotulosAcao = ROTULOS_ACAO;

  filtroEntidade = '';
  filtroAcao: AcaoAuditoria | '' = '';
  filtroDataInicio = '';
  filtroDataFim = '';

  pagina = 1;
  tamanho = 25;

  // Só uma linha expandida de cada vez — mesmo padrão de "só um editor
  // aberto" usado noutros ecrãs (ver documentos.component.ts).
  linhaExpandidaId: string | null = null;

  ngOnInit() {
    this.store.dispatch(AuditoriaActions.carregarEntidades({}));
    this.dispatchComFiltro(1);
  }

  private dispatchComFiltro(pagina: number) {
    this.store.dispatch(AuditoriaActions.carregarAuditoria({
      page: pagina, page_size: this.tamanho,
      filtros: {
        entidade: this.filtroEntidade || undefined,
        acao: (this.filtroAcao || undefined) as AcaoAuditoria | undefined,
        data_inicio: this.filtroDataInicio || undefined,
        data_fim: this.filtroDataFim || undefined,
      }
    }));
  }

  aplicarFiltros() {
    this.pagina = 1;
    this.dispatchComFiltro(1);
  }

  limparFiltros() {
    this.filtroEntidade = '';
    this.filtroAcao = '';
    this.filtroDataInicio = '';
    this.filtroDataFim = '';
    this.aplicarFiltros();
  }

  onPagina(pagina: number) {
    this.pagina = pagina;
    this.dispatchComFiltro(pagina);
  }

  onTamanho(tamanho: number) {
    this.tamanho = tamanho;
    this.pagina = 1;
    this.dispatchComFiltro(1);
  }

  onAlternarLinha(registoId: string) {
    this.linhaExpandidaId = this.linhaExpandidaId === registoId ? null : registoId;
  }

  // ALTERADO grava {campo: {antes, depois}}; CRIADO/APAGADO gravam um
  // snapshot simples {campo: valor} — ver core/auditoria.py. Distinguir
  // pelo formato em vez de confiar só em registo.acao evita rebentar
  // se um valor "normal" calhar de ser um objeto com essas duas chaves.
  ehDiferenca(valor: unknown): valor is AlteracaoCampo {
    return !!valor && typeof valor === 'object' && 'antes' in (valor as object) && 'depois' in (valor as object);
  }

  entradasAlteracoes(registo: AuditLogRegisto): [string, unknown][] {
    return registo.alteracoes ? Object.entries(registo.alteracoes) : [];
  }

  formatarValor(valor: unknown): string {
    if (valor === null || valor === undefined || valor === '') return '—';
    if (typeof valor === 'boolean') return valor ? 'Sim' : 'Não';
    return String(valor);
  }
}
