import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { AsyncPipe } from '@angular/common';
import { Store } from '@ngrx/store';
import { selectIsGestor } from '../../../store/auth/auth.selectors';

interface Periodo { id: string; nome: string; aberto: boolean; }
interface Pendencia { turma: string; disciplina: string; professor: string | null; total_alunos: number; sem_nota: number; alunos_sem_nota: string[]; }
interface PendenciasResp { periodo: string; ano_letivo: number | null; total_alunos_sem_nota: number; pendencias: Pendencia[]; }
interface DisciplinaResultado { nome: string; m_final: number | null; completa: boolean; aprovada: boolean | null; }
interface AlunoResultado {
  nome_completo: string; turma: string; resultado: 'APROVADO' | 'REPROVADO' | 'REPROVADO_FALTAS' | 'INCOMPLETO';
  resultado_atual: string | null; disciplinas: DisciplinaResultado[]; em_falta: string[]; faltas_percentagem: number;
}
interface Previa {
  ano_letivo: number; nota_minima_aprovacao: number | null; max_disciplinas_reprovadas: number; limite_faltas_percentagem: number | null;
  periodos_abertos: string[]; pode_fechar: boolean; ja_fechados: number;
  resumo: { total: number; aprovado: number; reprovado: number; reprovado_faltas: number; incompleto: number };
  alunos: AlunoResultado[];
}

/**
 * Fecho do trimestre (ver pendências e trancar) e do ano letivo (prévia dos
 * resultados finais, fechar, reabrir). As regras vivem em
 * back_end/app/core/resultados.py; aqui só se mostra e se confirma.
 */
@Component({
  selector: 'app-fecho-ano',
  imports: [FormsModule, AsyncPipe],
  template: `
    <div class="space-y-6">
      <div>
        <h2 class="text-2xl font-bold text-slate-800">Fecho do Trimestre e do Ano</h2>
        <p class="text-sm text-slate-500">Confirme que todas as notas estão lançadas, tranque o trimestre e, no fim do ano, feche os resultados finais dos alunos.</p>
      </div>

      @if (mensagem()) { <div role="status" class="bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm rounded-lg px-4 py-3">{{ mensagem() }}</div> }
      @if (erro()) { <div role="alert" class="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg px-4 py-3">{{ erro() }}</div> }

      <section class="bg-white p-6 rounded-xl shadow-xs border border-slate-200 space-y-4">
        <h3 class="text-sm font-semibold text-slate-800">1. Trimestres</h3>
        @for (p of periodos(); track p.id) {
          <div class="border border-slate-200 rounded-lg p-3">
            <div class="flex flex-wrap items-center gap-3">
              <span class="text-sm font-medium text-slate-700">{{ p.nome }}</span>
              <span class="text-xs font-medium py-0.5 px-2 rounded-full" [class.bg-emerald-100]="p.aberto" [class.text-emerald-700]="p.aberto"
                [class.bg-slate-200]="!p.aberto" [class.text-slate-700]="!p.aberto">{{ p.aberto ? 'Aberto' : 'Trancado' }}</span>
              <button type="button" (click)="verPendencias(p)" class="text-xs text-blue-600 hover:text-blue-800 font-medium cursor-pointer">Ver pendências</button>
              @if (p.aberto && (isGestor$ | async)) {
                <button type="button" (click)="trancar(p)" class="text-xs text-rose-600 hover:text-rose-800 font-medium cursor-pointer">Trancar trimestre</button>
              }
            </div>
            @if (pendencias()[p.id]; as r) {
              @if (r.total_alunos_sem_nota === 0) {
                <p class="text-xs text-emerald-700 mt-2">Sem pendências: todos os alunos têm nota neste trimestre.</p>
              } @else {
                <p class="text-xs text-amber-700 mt-2">{{ r.total_alunos_sem_nota }} nota(s) em falta. Trancar não impede — mas o fecho do ano só avança com tudo lançado.</p>
                <ul class="mt-2 space-y-1">
                  @for (x of r.pendencias; track x.turma + x.disciplina) {
                    <li class="text-xs text-slate-600">
                      <strong>{{ x.turma }}</strong> · {{ x.disciplina }}
                      @if (x.professor) { ({{ x.professor }}) }
                      — faltam {{ x.sem_nota }} de {{ x.total_alunos }}: {{ x.alunos_sem_nota.join(', ') }}
                    </li>
                  }
                </ul>
              }
            }
          </div>
        } @empty {
          <p class="text-sm text-slate-500">Ainda não há trimestres registados. Crie-os no Diário de Classe.</p>
        }
      </section>

      <section class="bg-white p-6 rounded-xl shadow-xs border border-slate-200 space-y-4">
        <h3 class="text-sm font-semibold text-slate-800">2. Fecho do ano letivo</h3>
        <div class="flex flex-wrap items-end gap-3">
          <div>
            <label class="block text-xs font-medium text-slate-600 mb-1" for="f-fecho-ano-1">Ano letivo (ano de início)</label>
            <input type="number" [(ngModel)]="ano" class="w-32 border border-slate-300 rounded-lg px-3 py-1.5 text-sm" id="f-fecho-ano-1" />
          </div>
          <button type="button" (click)="carregarPrevia()" class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 px-4 rounded-lg cursor-pointer">Ver prévia dos resultados</button>
        </div>

        @if (previa(); as pv) {
          <div class="text-xs text-slate-500">
            Critérios: nota mínima {{ pv.nota_minima_aprovacao ?? 'não definida' }} · disciplinas em atraso permitidas {{ pv.max_disciplinas_reprovadas }} ·
            limite de faltas {{ pv.limite_faltas_percentagem != null ? pv.limite_faltas_percentagem + '%' : 'sem limite' }}
            (mude em Configurações).
          </div>
          <div class="flex flex-wrap gap-2 text-xs font-medium">
            <span class="py-1 px-3 rounded-full bg-emerald-100 text-emerald-700">{{ pv.resumo.aprovado }} aprovados</span>
            <span class="py-1 px-3 rounded-full bg-rose-100 text-rose-700">{{ pv.resumo.reprovado }} reprovados</span>
            <span class="py-1 px-3 rounded-full bg-rose-100 text-rose-700">{{ pv.resumo.reprovado_faltas }} por faltas</span>
            <span class="py-1 px-3 rounded-full bg-amber-100 text-amber-700">{{ pv.resumo.incompleto }} com notas em falta</span>
            <span class="py-1 px-3 rounded-full bg-slate-100 text-slate-600">{{ pv.ja_fechados }} já fechados</span>
          </div>

          @if (pv.nota_minima_aprovacao == null) {
            <p class="text-sm text-amber-700">Defina a nota mínima de aprovação em Configurações para poder fechar o ano.</p>
          }
          @if (pv.periodos_abertos.length) {
            <p class="text-sm text-amber-700">Tranque primeiro: {{ pv.periodos_abertos.join(', ') }}.</p>
          }

          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead><tr class="text-slate-500 border-b border-slate-200">
                <th class="py-2 pr-4 font-medium">Aluno</th><th class="py-2 pr-4 font-medium">Turma</th>
                <th class="py-2 pr-4 font-medium">Resultado</th><th class="py-2 font-medium">Detalhe</th>
              </tr></thead>
              <tbody>
                @for (a of pv.alunos; track a.nome_completo + a.turma) {
                  <tr class="border-b border-slate-100">
                    <td class="py-2 pr-4 text-slate-800">{{ a.nome_completo }}</td>
                    <td class="py-2 pr-4 text-slate-600">{{ a.turma }}</td>
                    <td class="py-2 pr-4">
                      <span class="text-xs font-medium py-1 px-3 rounded-full" [class]="classe(a.resultado)">{{ rotulo(a.resultado) }}</span>
                      @if (a.resultado_atual) { <span class="text-xs text-slate-400 ml-1">(gravado)</span> }
                    </td>
                    <td class="py-2 text-xs text-slate-500">
                      @if (a.em_falta.length) { Notas em falta: {{ a.em_falta.join(', ') }} }
                      @else { {{ a.disciplinas.length }} disciplina(s); faltas {{ a.faltas_percentagem }}% }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          @if (isGestor$ | async) {
            <div class="flex flex-wrap gap-3 pt-2">
              @if (!confirmarFecho) {
                <button type="button" [disabled]="!pv.pode_fechar" (click)="confirmarFecho = true"
                  class="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-medium py-2 px-4 rounded-lg cursor-pointer">Fechar o ano</button>
              } @else {
                <span class="text-sm text-slate-600 self-center">Grava o resultado de {{ pv.resumo.aprovado + pv.resumo.reprovado + pv.resumo.reprovado_faltas }} aluno(s). Confirmar?</span>
                <button type="button" (click)="fechar()" class="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium py-2 px-4 rounded-lg cursor-pointer">Sim, fechar</button>
                <button type="button" (click)="confirmarFecho = false" class="bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2 px-4 rounded-lg cursor-pointer">Cancelar</button>
              }
              @if (pv.ja_fechados > 0) {
                <button type="button" (click)="reabrir()" class="bg-rose-100 hover:bg-rose-200 text-rose-700 text-sm font-medium py-2 px-4 rounded-lg cursor-pointer">Reabrir o fecho (anula os resultados)</button>
              }
            </div>
          } @else {
            <p class="text-xs text-slate-400">Só o Gestor pode fechar ou reabrir o ano.</p>
          }
        }
      </section>
    </div>
  `,
})
export class FechoAnoComponent implements OnInit {
  private http = inject(HttpClient);
  private store = inject(Store);

  isGestor$ = this.store.select(selectIsGestor);
  periodos = signal<Periodo[]>([]);
  pendencias = signal<Record<string, PendenciasResp>>({});
  previa = signal<Previa | null>(null);
  mensagem = signal<string | null>(null);
  erro = signal<string | null>(null);
  ano = new Date().getFullYear();
  confirmarFecho = false;

  ngOnInit() { this.carregarPeriodos(); }

  private falha = (err: any) => this.erro.set(err.error?.detail || 'Não foi possível concluir a operação.');

  carregarPeriodos() {
    this.http.get<Periodo[]>('/api/v1/diario/periodos').subscribe({ next: p => this.periodos.set(p), error: this.falha });
  }

  verPendencias(p: Periodo) {
    this.erro.set(null);
    this.http.get<PendenciasResp>(`/api/v1/fecho/periodos/${p.id}/pendencias`).subscribe({
      next: r => this.pendencias.update(m => ({ ...m, [p.id]: r })), error: this.falha,
    });
  }

  trancar(p: Periodo) {
    this.erro.set(null);
    this.http.patch(`/api/v1/diario/periodos/${p.id}/trancar`, {}).subscribe({
      next: () => { this.mensagem.set(`${p.nome} trancado.`); this.carregarPeriodos(); }, error: this.falha,
    });
  }

  carregarPrevia(limparMensagem = true) {
    this.erro.set(null); this.confirmarFecho = false;
    if (limparMensagem) this.mensagem.set(null);
    this.http.get<Previa>(`/api/v1/fecho/ano/${this.ano}/previa`).subscribe({ next: r => this.previa.set(r), error: this.falha });
  }

  fechar() {
    this.confirmarFecho = false;
    this.http.post<{ fechados: number; incompletos: unknown[]; completo: boolean }>(`/api/v1/fecho/ano/${this.ano}`, {}).subscribe({
      next: r => {
        this.mensagem.set(r.completo ? `Ano fechado: ${r.fechados} resultado(s) gravado(s).`
          : `${r.fechados} resultado(s) gravado(s). ${r.incompletos.length} aluno(s) ficaram por fechar por terem notas em falta — corrija e volte a fechar.`);
        this.carregarPrevia(false);
      },
      error: this.falha,
    });
  }

  reabrir() {
    this.http.post<{ reabertas: number }>(`/api/v1/fecho/ano/${this.ano}/reabrir`, {}).subscribe({
      next: r => { this.mensagem.set(`Fecho reaberto: ${r.reabertas} resultado(s) anulado(s).`); this.carregarPrevia(false); }, error: this.falha,
    });
  }

  rotulo(r: string) {
    return { APROVADO: 'Aprovado', REPROVADO: 'Reprovado', REPROVADO_FALTAS: 'Reprovado por faltas', INCOMPLETO: 'Notas em falta' }[r] ?? r;
  }

  classe(r: string) {
    return r === 'APROVADO' ? 'bg-emerald-100 text-emerald-700' : r === 'INCOMPLETO' ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700';
  }
}
