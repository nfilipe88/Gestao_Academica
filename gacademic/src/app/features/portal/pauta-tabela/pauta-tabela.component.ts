import { CommonModule, DatePipe } from '@angular/common';
import { Component, Input } from '@angular/core';
import { DisciplinaPauta, Pauta, PeriodoPauta } from '../../../store/portal/portal.models';

/**
 * Tabela estruturada da Pauta (estilo MININED) — reutilizada no
 * Dashboard do aluno (ano corrente, sem seletor) e no separador Pauta
 * (com seletor de Ano Letivo, ver portal.component.html). Reutilizável
 * em vez de duplicar o template porque a estrutura (MACT/PT/MT/Faltas
 * por período + MFD/MEO/NEN/M.Final) é grande demais para repetir em
 * dois sítios sem arriscar as duas cópias divergirem.
 */
@Component({
  selector: 'app-pauta-tabela',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './pauta-tabela.component.html',
})
export class PautaTabelaComponent {
  @Input({ required: true }) pauta: Pauta | null = null;
  @Input() colunas: string[] = [];

  periodoDaDisciplina(disciplina: DisciplinaPauta, periodoNome: string): PeriodoPauta | undefined {
    return disciplina.periodos.find(p => p.periodo_avaliacao === periodoNome);
  }

  // MACT/PT estruturados só quando esses dois tipos existem no
  // período (escolas que importaram mini-pautas MININED); senão a
  // lista genérica em chips (já existia) continua a servir escolas
  // com CONTINUA/PROVA ou tipos próprios.
  mact(periodo: PeriodoPauta) {
    return periodo.avaliacoes.find(a => a.tipo_avaliacao === 'MACT');
  }

  pt(periodo: PeriodoPauta) {
    return periodo.avaliacoes.find(a => a.tipo_avaliacao === 'PT');
  }

  temMactPtEstruturado(periodo: PeriodoPauta): boolean {
    return !!this.mact(periodo) && !!this.pt(periodo);
  }
}
