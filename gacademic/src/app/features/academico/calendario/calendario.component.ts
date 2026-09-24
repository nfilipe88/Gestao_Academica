import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe, AsyncPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Store } from '@ngrx/store';
import { selectIsGestor } from '../../../store/auth/auth.selectors';

type Tipo = 'PERIODO_LETIVO' | 'AVALIACOES' | 'EXAMES' | 'EXAMES_FINAIS' | 'EXAMES_RECURSO' | 'OUTRO';
interface Entrada {
  id: string | null; ano_letivo: number; tipo: Tipo; nome: string; data_inicio: string | null; data_fim: string | null;
  observacoes: string | null; origem: 'CALENDARIO' | 'DIARIO'; estado: 'DECORRER' | 'PROXIMO' | 'TERMINADO' | null;
}

const TIPOS: { valor: Tipo; rotulo: string; cor: string }[] = [
  { valor: 'PERIODO_LETIVO', rotulo: 'Período letivo', cor: 'bg-blue-100 text-blue-700' },
  { valor: 'AVALIACOES', rotulo: 'Período de avaliações', cor: 'bg-violet-100 text-violet-700' },
  { valor: 'EXAMES', rotulo: 'Exames', cor: 'bg-amber-100 text-amber-800' },
  { valor: 'EXAMES_FINAIS', rotulo: 'Exames finais', cor: 'bg-orange-100 text-orange-800' },
  { valor: 'EXAMES_RECURSO', rotulo: 'Exames de recurso', cor: 'bg-rose-100 text-rose-700' },
  { valor: 'OUTRO', rotulo: 'Outro (férias, feriados…)', cor: 'bg-slate-200 text-slate-700' },
];

/**
 * Calendário do ano letivo. Qualquer perfil do pessoal lê; só o Gestor edita
 * (back_end/app/api/v1/calendario.py). Mostra também, só em leitura, os
 * trimestres do Diário de Classe que já têm janela de datas.
 */
@Component({
  selector: 'app-calendario',
  imports: [FormsModule, DatePipe, AsyncPipe],
  template: `
    <div class="space-y-6">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 class="text-2xl font-bold text-slate-800">Calendário Letivo</h2>
          <p class="text-sm text-slate-500">Períodos letivos, avaliações, exames, exames finais e exames de recurso do ano.</p>
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-600 mb-1" for="f-calendario-1">Ano letivo (ano de início)</label>
          <input type="number" [(ngModel)]="ano" (change)="carregar()" class="w-28 border border-slate-300 rounded-lg px-3 py-1.5 text-sm" id="f-calendario-1" />
        </div>
      </div>

      @if (erro()) { <div role="alert" class="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded-lg px-4 py-3">{{ erro() }}</div> }

      @if (isGestor$ | async) {
        <form (ngSubmit)="guardar()" class="bg-white p-5 rounded-xl shadow-xs border border-slate-200 grid gap-3 sm:grid-cols-2 lg:grid-cols-5 items-end">
          <div>
            <label class="block text-xs font-medium text-slate-600 mb-1" for="f-calendario-2">Tipo</label>
            <select name="tipo" [(ngModel)]="novo.tipo" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" id="f-calendario-2">
              @for (t of tipos; track t.valor) { <option [value]="t.valor">{{ t.rotulo }}</option> }
            </select>
          </div>
          <div class="lg:col-span-2">
            <label class="block text-xs font-medium text-slate-600 mb-1" for="f-calendario-3">Nome</label>
            <input name="nome" [(ngModel)]="novo.nome" required minlength="2" placeholder="Ex.: Exames do 1º trimestre" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" id="f-calendario-3" />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-600 mb-1" for="f-calendario-4">Início</label>
            <input type="date" name="ini" [(ngModel)]="novo.data_inicio" required class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" id="f-calendario-4" />
          </div>
          <div>
            <label class="block text-xs font-medium text-slate-600 mb-1" for="f-calendario-5">Fim</label>
            <input type="date" name="fim" [(ngModel)]="novo.data_fim" required class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" id="f-calendario-5" />
          </div>
          <div class="sm:col-span-2 lg:col-span-4">
            <input name="obs" [(ngModel)]="novo.observacoes" placeholder="Observações (opcional)" class="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 px-4 rounded-lg cursor-pointer">Adicionar ao calendário</button>
        </form>
      }

      <div class="bg-white rounded-xl shadow-xs border border-slate-200 divide-y divide-slate-100">
        @for (e of entradas(); track (e.id ?? e.nome + e.data_inicio)) {
          <div class="flex flex-wrap items-center gap-3 px-5 py-3">
            <span class="text-xs font-medium py-1 px-3 rounded-full min-w-40 text-center" [class]="cor(e.tipo)">{{ rotulo(e.tipo) }}</span>
            <div class="flex-1 min-w-48">
              <p class="text-sm font-medium text-slate-800">{{ e.nome }}</p>
              @if (e.observacoes) { <p class="text-xs text-slate-400">{{ e.observacoes }}</p> }
            </div>
            <p class="text-sm text-slate-600">{{ e.data_inicio | date:'dd/MM/yyyy' }} – {{ e.data_fim | date:'dd/MM/yyyy' }}</p>
            @if (e.estado === 'DECORRER') { <span class="text-xs font-medium py-0.5 px-2 rounded-full bg-emerald-100 text-emerald-700">A decorrer</span> }
            @else if (e.estado === 'PROXIMO') { <span class="text-xs font-medium py-0.5 px-2 rounded-full bg-sky-100 text-sky-700">Próximo</span> }
            @else if (e.estado === 'TERMINADO') { <span class="text-xs font-medium py-0.5 px-2 rounded-full bg-slate-100 text-slate-500">Terminado</span> }
            @if (e.id && (isGestor$ | async)) {
              <button type="button" (click)="remover(e)" class="text-xs text-rose-600 hover:text-rose-800 font-medium cursor-pointer">Remover</button>
            }
          </div>
        } @empty {
          <p class="px-5 py-8 text-sm text-slate-500 text-center">Ainda não há marcos definidos para {{ ano }}/{{ ano + 1 }}.</p>
        }
      </div>
    </div>
  `,
})
export class CalendarioComponent implements OnInit {
  private http = inject(HttpClient);
  private store = inject(Store);

  isGestor$ = this.store.select(selectIsGestor);
  tipos = TIPOS;
  entradas = signal<Entrada[]>([]);
  erro = signal<string | null>(null);
  ano = new Date().getFullYear();
  novo: { tipo: Tipo; nome: string; data_inicio: string; data_fim: string; observacoes: string } =
    { tipo: 'PERIODO_LETIVO', nome: '', data_inicio: '', data_fim: '', observacoes: '' };

  ngOnInit() { this.carregar(); }

  private falha = (err: any) => {
    const detalhe = err.error?.detail;
    this.erro.set(typeof detalhe === 'string' ? detalhe : 'Não foi possível concluir a operação. Confirme os campos.');
  };

  rotulo(t: string) { return TIPOS.find(x => x.valor === t)?.rotulo ?? t; }
  cor(t: string) { return TIPOS.find(x => x.valor === t)?.cor ?? ''; }

  carregar() {
    this.http.get<Entrada[]>(`/api/v1/calendario?ano_letivo=${this.ano}`).subscribe({
      next: r => { this.erro.set(null); this.entradas.set(r); }, error: this.falha,
    });
  }

  guardar() {
    this.erro.set(null);
    const corpo = { ...this.novo, ano_letivo: this.ano, observacoes: this.novo.observacoes || null };
    this.http.post('/api/v1/calendario', corpo).subscribe({
      next: () => { this.novo = { ...this.novo, nome: '', observacoes: '' }; this.carregar(); }, error: this.falha,
    });
  }

  remover(e: Entrada) {
    this.http.delete(`/api/v1/calendario/${e.id}`).subscribe({ next: () => this.carregar(), error: this.falha });
  }
}
