import { AsyncPipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import { firstValueFrom } from 'rxjs';
import { carregarTurmas } from '../../../../store/academico/academic.actions';
import { selectTurmas } from '../../../../store/academico/academic.selector';
import { Turma } from '../../../../store/academico/academic.models';

interface CandidatoRematricula {
  aluno_id: string;
  nome_completo: string;
  matricula_interna: string;
  matricula_atual_id: string;
  turma_atual_id: string;
  nome_turma_atual: string;
  // RN05 (ver app/cruds/matriculas.py::tem_mensalidade_em_atraso_de_ano_anterior)
  // — exatamente o mesmo bloqueio que POST /matriculas vai aplicar.
  bloqueado_por_atraso: boolean;
  // A família já confirmou interesse no Portal (ver
  // app/cruds/portal.py::pedir_rematricula) — prioriza estes primeiro.
  pedido_confirmado_pela_familia: boolean;
}

interface RespostaCandidatosRematricula {
  ano_letivo_origem: number | null;
  ano_letivo_destino: number | null;
  candidatos: CandidatoRematricula[];
}

/**
 * Ecrã dedicado de Rematrícula — lista os alunos ATIVOS de um ano
 * letivo de origem que ainda não têm matrícula no ano seguinte, e
 * permite renovar vários de uma vez (cada um escolhe/recebe uma turma
 * de destino). Não é uma rota nova no back-end para "renovar" em si —
 * cada renovação é só a mesma POST /matriculas de sempre, aplicada em
 * lote a partir daqui; RN05 (mensalidade em atraso de ano anterior)
 * continua a ser a mesma regra, só fica visível ANTES de tentar (ver
 * GET /matriculas/rematricula-candidatos).
 */
@Component({
  selector: 'app-rematricula.component',
  imports: [AsyncPipe, FormsModule],
  templateUrl: './rematricula.component.html',
  styleUrl: './rematricula.component.css',
})
export class RematriculaComponent implements OnInit {
  private http = inject(HttpClient);
  private store = inject(Store);

  turmas$ = this.store.select(selectTurmas);

  anoLetivoOrigem = signal<number | null>(null);
  anoLetivoDestino = signal<number | null>(null);
  candidatos = signal<CandidatoRematricula[]>([]);
  aCarregar = signal(true);
  erro = signal<string | null>(null);

  // Seleção + turma de destino por aluno — objetos simples (não signal):
  // só lidos em métodos disparados por clique, nunca precisam de
  // acionar re-render sozinhos (o próprio clique já o faz).
  selecionados: Record<string, boolean> = {};
  turmaDestinoPorAluno: Record<string, string> = {};
  turmaDestinoEmLote = '';

  aRenovar = signal(false);
  resultadoPorAluno = signal<Record<string, 'ok' | 'erro'>>({});
  erroPorAluno: Record<string, string> = {};

  ngOnInit() {
    this.store.dispatch(carregarTurmas());
    this.carregarCandidatos();
  }

  carregarCandidatos(anoLetivo?: number) {
    this.aCarregar.set(true);
    this.erro.set(null);
    const params: Record<string, string> = {};
    if (anoLetivo) params['ano_letivo'] = String(anoLetivo);
    this.http.get<RespostaCandidatosRematricula>('/api/v1/matriculas/rematricula-candidatos', { params }).subscribe({
      next: (resp) => {
        this.anoLetivoOrigem.set(resp.ano_letivo_origem);
        this.anoLetivoDestino.set(resp.ano_letivo_destino);
        this.candidatos.set(resp.candidatos);
        this.selecionados = {};
        this.turmaDestinoPorAluno = {};
        this.resultadoPorAluno.set({});
        this.erroPorAluno = {};
        this.aCarregar.set(false);
      },
      error: (err) => {
        this.aCarregar.set(false);
        this.erro.set(err.error?.detail || 'Não foi possível carregar os candidatos a rematrícula.');
      },
    });
  }

  onMudarAnoOrigem(valor: string) {
    const ano = Number(valor);
    if (!ano) return;
    this.carregarCandidatos(ano);
  }

  turmasDoAnoDestino(turmas: Turma[] | null): Turma[] {
    const anoDestino = this.anoLetivoDestino();
    if (!turmas || !anoDestino) return [];
    return turmas.filter(t => t.ano_letivo === anoDestino);
  }

  // Só quem não está bloqueado por atraso pode ser selecionado — RN05
  // ia recusar de qualquer forma, é melhor nunca deixar tentar.
  candidatosSelecionaveis(): CandidatoRematricula[] {
    return this.candidatos().filter(c => !c.bloqueado_por_atraso);
  }

  todosSelecionados(): boolean {
    const selecionaveis = this.candidatosSelecionaveis();
    return selecionaveis.length > 0 && selecionaveis.every(c => this.selecionados[c.aluno_id]);
  }

  onAlternarTodos(marcar: boolean) {
    for (const c of this.candidatosSelecionaveis()) {
      this.selecionados[c.aluno_id] = marcar;
    }
  }

  onAplicarTurmaEmLote() {
    if (!this.turmaDestinoEmLote) return;
    for (const c of this.candidatos()) {
      if (this.selecionados[c.aluno_id]) {
        this.turmaDestinoPorAluno[c.aluno_id] = this.turmaDestinoEmLote;
      }
    }
  }

  contagemSelecionados(): number {
    return Object.values(this.selecionados).filter(Boolean).length;
  }

  contagemProntosParaRenovar(): number {
    return this.candidatos().filter(c => this.selecionados[c.aluno_id] && this.turmaDestinoPorAluno[c.aluno_id]).length;
  }

  // Sequencial (não Promise.all) de propósito: cada POST /matriculas é
  // independente, mas correr todas em paralelo contra a mesma escola
  // dava um pico de N ligações simultâneas para uma ação em lote que
  // ninguém está a cronometrar ao segundo — aqui o ritmo importa mais
  // que a velocidade.
  async onRenovarSelecionados() {
    const anoDestino = this.anoLetivoDestino();
    if (!anoDestino) return;
    const alvos = this.candidatos().filter(c => this.selecionados[c.aluno_id] && this.turmaDestinoPorAluno[c.aluno_id]);
    if (alvos.length === 0) return;

    this.aRenovar.set(true);
    const resultados: Record<string, 'ok' | 'erro'> = {};
    this.erroPorAluno = {};

    for (const candidato of alvos) {
      const turmaId = this.turmaDestinoPorAluno[candidato.aluno_id];
      try {
        await firstValueFrom(this.http.post('/api/v1/matriculas', {
          aluno_id: candidato.aluno_id, turma_id: turmaId, ano_letivo: anoDestino,
        }));
        resultados[candidato.aluno_id] = 'ok';
      } catch (err: any) {
        resultados[candidato.aluno_id] = 'erro';
        this.erroPorAluno[candidato.aluno_id] = err.error?.detail || 'Não foi possível renovar.';
      }
    }

    this.resultadoPorAluno.set(resultados);
    this.aRenovar.set(false);
    // Só desaparecem da lista os que renovaram com sucesso — os que
    // falharam ficam visíveis com o erro, para se corrigir e tentar de novo.
    this.candidatos.set(this.candidatos().filter(c => resultados[c.aluno_id] !== 'ok'));
  }
}
