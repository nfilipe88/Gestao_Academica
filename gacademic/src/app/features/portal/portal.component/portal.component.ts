import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Actions, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { filter, take } from 'rxjs';
import { selectUsuario } from '../../../store/auth/auth.selectors';
import { capturarPagamento, financeiroOperacaoSucesso, gerarCobranca } from '../../../store/financeiro/financeiro.actions';
import { selectUltimaCobranca } from '../../../store/financeiro/financeiro.selector';
import {
  carregarBoletimDoEducando, carregarFinanceiroDoEducando, carregarHorarioDoEducando, carregarMeusEducandos
} from '../../../store/portal/portal.actions';
import {
  selectBoletimDoEducando, selectFinanceiroDoEducando, selectHorarioDoEducando,
  selectMeusEducandos, selectPortalError
} from '../../../store/portal/portal.selector';
import { HorarioAulaPortal } from '../../../store/portal/portal.models';

// 1=Segunda ... 7=Domingo (ISO 8601), igual ao módulo Horários.
const DIAS_DA_SEMANA = [
  { valor: 1, nome: 'Segunda' },
  { valor: 2, nome: 'Terça' },
  { valor: 3, nome: 'Quarta' },
  { valor: 4, nome: 'Quinta' },
  { valor: 5, nome: 'Sexta' },
  { valor: 6, nome: 'Sábado' },
];

@Component({
  selector: 'app-portal.component',
  imports: [CommonModule, AsyncPipe],
  templateUrl: './portal.component.html',
  styleUrl: './portal.component.css',
})
export class PortalComponent implements OnInit {
  private store = inject(Store);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private actions$ = inject(Actions);

  usuario$ = this.store.select(selectUsuario);
  educandos$ = this.store.select(selectMeusEducandos);
  horario$ = this.store.select(selectHorarioDoEducando);
  boletim$ = this.store.select(selectBoletimDoEducando);
  financeiro$ = this.store.select(selectFinanceiroDoEducando);
  erro$ = this.store.select(selectPortalError);

  dias = DIAS_DA_SEMANA;

  educandoSelecionadoId: string | null = null;
  aba: 'horario' | 'boletim' | 'financeiro' = 'horario';

  ngOnInit() {
    this.store.dispatch(carregarMeusEducandos());

    // Depois do PayPal redirecionar de volta (return_url gerado em
    // POST /financeiro/faturas/{id}/gerar-cobranca, apontado para cá
    // quando quem paga é RESPONSAVEL/ALUNO), a página recarrega do
    // zero — o aluno_id vem na própria URL para repormos a seleção.
    const params = this.route.snapshot.queryParamMap;
    const alunoId = params.get('aluno_id');
    const retorno = params.get('paypal_retorno');
    const token = params.get('token'); // PayPal chama o order_id de "token" no redirecionamento

    if (alunoId) {
      this.onSelecionarEducando(alunoId);
    }
    if (retorno === 'sucesso' && token && alunoId) {
      this.financeiro$.pipe(filter(f => !!f?.contrato), take(1)).subscribe(financeiro => {
        this.store.dispatch(capturarPagamento({ order_id: token, contrato_id: financeiro!.contrato!.id }));
        // capturarPagamento$ só atualiza store/financeiro, não
        // store/portal — só refrescamos este depois de confirmado
        // (financeiroOperacaoSucesso), para não sobrepor com dados
        // ainda por capturar.
        this.actions$.pipe(ofType(financeiroOperacaoSucesso), take(1)).subscribe(() => {
          this.store.dispatch(carregarFinanceiroDoEducando({ aluno_id: alunoId }));
        });
      });
    }
    if (retorno) {
      this.router.navigate([], { relativeTo: this.route, queryParams: {}, replaceUrl: true });
    }
  }

  onSelecionarEducando(alunoId: string) {
    this.educandoSelecionadoId = alunoId;
    this.aba = 'horario';
    this.store.dispatch(carregarHorarioDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarBoletimDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarFinanceiroDoEducando({ aluno_id: alunoId }));
  }

  slotsDoDia(horarios: HorarioAulaPortal[] | null, dia: number): HorarioAulaPortal[] {
    if (!horarios) return [];
    return horarios.filter(h => h.dia_semana === dia).sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));
  }

  formatarHora(hora: string): string {
    return hora?.substring(0, 5) ?? '';
  }

  onPagarComPayPal(faturaId: string, contratoId: string) {
    // Abre já a aba em branco, de forma síncrona, dentro do próprio
    // handler de clique — é isto que impede o browser de bloquear como
    // pop-up. Só depois é que sabemos a approve_url (vem do back-end),
    // altura em que só falta redirecionar esta aba já aberta. Mesmo
    // padrão da página Financeiro (Gestor/Secretaria) — reaproveita a
    // mesma action/effect de gerarCobranca (já com o controlo de posse
    // no back-end, ver cruds/financeiro.py).
    const aba = window.open('', '_blank');
    this.store.dispatch(gerarCobranca({ fatura_id: faturaId, contrato_id: contratoId, metodo_pagamento: 'PAYPAL' }));

    this.store.select(selectUltimaCobranca).pipe(
      filter(cobranca => !!cobranca && cobranca.fatura_id === faturaId),
      take(1)
    ).subscribe(cobranca => {
      const approveUrl = cobranca?.dados_pagamento?.approve_url;
      if (aba && approveUrl) {
        aba.location.href = approveUrl;
      } else if (aba) {
        aba.close();
      }
      // O effect gerarCobranca$ atualiza store/financeiro (usado pela
      // página do Gestor/Secretaria), não store/portal — sem isto, o
      // botão "Pagar com PayPal" não passava a "Continuar pagamento
      // PayPal" nesta página.
      if (this.educandoSelecionadoId) {
        this.store.dispatch(carregarFinanceiroDoEducando({ aluno_id: this.educandoSelecionadoId }));
      }
    });
  }
}
