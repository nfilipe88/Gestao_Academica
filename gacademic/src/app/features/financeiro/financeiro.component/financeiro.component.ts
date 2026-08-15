import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { filter, take } from 'rxjs';
import { carregarAlunos } from '../../../store/alunos/alunos.actions';
import { selectAlunos } from '../../../store/alunos/alunos.selector';
import { selectIsGestorOuSecretaria } from '../../../store/auth/auth.selectors';
import { selectMoeda } from '../../../store/configuracoes/configuracoes.selector';
import {
  capturarPagamento, carregarContratoDaMatricula, carregarMatriculasDoAluno, carregarResponsaveisDaMatricula,
  criarContrato, gerarCobranca, marcarFaturaPaga, processarReguaCobranca
} from '../../../store/financeiro/financeiro.actions';
import {
  selectContrato, selectContratoCarregado, selectFaturas, selectFinanceiroError,
  selectFinanceiroMensagem, selectMatriculasDoAluno, selectResponsaveisElegiveis, selectUltimaCobranca
} from '../../../store/financeiro/financeiro.selector';
import { abrirOuNavegar } from '../../../core/utils/abrir-em-nova-aba';

const FORMAS_PAGAMENTO = ['MANUAL', 'DINHEIRO', 'TRANSFERENCIA', 'MBWAY', 'OUTRO'];

@Component({
  selector: 'app-financeiro.component',
  imports: [ReactiveFormsModule, FormsModule, CommonModule, AsyncPipe],
  templateUrl: './financeiro.component.html',
  styleUrl: './financeiro.component.css',
})
export class FinanceiroComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  alunos$ = this.store.select(selectAlunos);
  matriculas$ = this.store.select(selectMatriculasDoAluno);
  responsaveis$ = this.store.select(selectResponsaveisElegiveis);
  contrato$ = this.store.select(selectContrato);
  contratoCarregado$ = this.store.select(selectContratoCarregado);
  faturas$ = this.store.select(selectFaturas);
  erro$ = this.store.select(selectFinanceiroError);
  mensagem$ = this.store.select(selectFinanceiroMensagem);
  podeGerir$ = this.store.select(selectIsGestorOuSecretaria);
  moeda$ = this.store.select(selectMoeda);

  formasPagamento = FORMAS_PAGAMENTO;

  alunoSelecionadoId = '';
  matriculaSelecionadaId: string | null = null;

  mostrarFormularioContrato = false;
  formaPagamentoPorFatura: Record<string, string> = {};

  contratoForm = this.fb.group({
    responsavel_id: ['', Validators.required],
    valor_total_anual: [null as number | null, [Validators.required, Validators.min(0.01)]],
    quantidade_parcelas: [12, [Validators.required, Validators.min(1), Validators.max(36)]],
    dia_vencimento_padrao: [5, [Validators.required, Validators.min(1), Validators.max(28)]],
    percentual_desconto_bolsa: [0, [Validators.min(0), Validators.max(100)]]
  });

  // Mensagem local (não vem do back-end) para o caso "cancelado" do
  // redirecionamento do PayPal — não há nada para o effects tratar aí.
  pagamentoCanceladoLocalmente = false;

  ngOnInit() {
    this.store.dispatch(carregarAlunos({ page_size: 100 })); // povoa um <select>, ver nota em transferencias.component.ts

    // Depois do PayPal redirecionar de volta (ver return_url/cancel_url
    // gerados em POST /financeiro/faturas/{id}/gerar-cobranca), a página
    // recarrega do zero — a matrícula selecionada vem na própria URL
    // para conseguirmos repor o extrato sem o utilizador escolher tudo outra vez.
    const params = this.route.snapshot.queryParamMap;
    const matriculaId = params.get('matricula_id');
    const retorno = params.get('paypal_retorno');
    const token = params.get('token'); // PayPal chama o order_id de "token" no redirecionamento

    if (matriculaId) {
      this.onSelecionarMatricula(matriculaId);
    }

    if (retorno === 'sucesso' && token) {
      this.contrato$.pipe(filter(c => !!c), take(1)).subscribe(contrato => {
        this.store.dispatch(capturarPagamento({ order_id: token, contrato_id: contrato!.id }));
      });
    } else if (retorno === 'cancelado') {
      this.pagamentoCanceladoLocalmente = true;
    }

    // Limpa os parâmetros do PayPal da URL para um refresh da página não
    // tentar capturar/reprocessar a mesma Order outra vez.
    if (retorno) {
      this.router.navigate([], { relativeTo: this.route, queryParams: {}, replaceUrl: true });
    }
  }

  onSelecionarAluno(alunoId: string) {
    this.alunoSelecionadoId = alunoId;
    this.matriculaSelecionadaId = null;
    this.mostrarFormularioContrato = false;
    if (alunoId) {
      this.store.dispatch(carregarMatriculasDoAluno({ aluno_id: alunoId }));
    }
  }

  onSelecionarMatricula(matriculaId: string) {
    this.matriculaSelecionadaId = matriculaId || null;
    this.mostrarFormularioContrato = false;
    if (this.matriculaSelecionadaId) {
      this.store.dispatch(carregarContratoDaMatricula({ matricula_id: this.matriculaSelecionadaId }));
      this.store.dispatch(carregarResponsaveisDaMatricula({ matricula_id: this.matriculaSelecionadaId }));
    }
  }

  alternarFormularioContrato() {
    this.mostrarFormularioContrato = !this.mostrarFormularioContrato;
    this.contratoForm.reset({ quantidade_parcelas: 12, dia_vencimento_padrao: 5, percentual_desconto_bolsa: 0 });
  }

  onSubmitContrato() {
    if (this.contratoForm.invalid || !this.matriculaSelecionadaId) return;
    const { responsavel_id, valor_total_anual, quantidade_parcelas, dia_vencimento_padrao, percentual_desconto_bolsa } = this.contratoForm.value;
    this.store.dispatch(criarContrato({
      matricula_id: this.matriculaSelecionadaId,
      responsavel_id: responsavel_id!,
      valor_total_anual: valor_total_anual!,
      quantidade_parcelas: quantidade_parcelas!,
      dia_vencimento_padrao: dia_vencimento_padrao!,
      percentual_desconto_bolsa: percentual_desconto_bolsa ?? 0
    }));
    this.mostrarFormularioContrato = false;
  }

  onMarcarPago(faturaId: string, contratoId: string) {
    const forma = this.formaPagamentoPorFatura[faturaId] || 'MANUAL';
    this.store.dispatch(marcarFaturaPaga({ fatura_id: faturaId, contrato_id: contratoId, valor_pago: null, forma_pagamento: forma }));
  }

  onPagarComPayPal(faturaId: string, contratoId: string) {
    // Abre já a aba em branco, de forma síncrona, dentro do próprio
    // handler de clique — é isto que impede o browser de bloquear como
    // pop-up. Só depois é que sabemos a approve_url (vem do back-end),
    // altura em que só falta redirecionar esta aba já aberta.
    const aba = window.open('', '_blank');
    this.store.dispatch(gerarCobranca({ fatura_id: faturaId, contrato_id: contratoId, metodo_pagamento: 'PAYPAL' }));

    this.store.select(selectUltimaCobranca).pipe(
      filter(cobranca => !!cobranca && cobranca.fatura_id === faturaId),
      take(1)
    ).subscribe(cobranca => {
      const approveUrl = cobranca?.dados_pagamento?.approve_url;
      if (approveUrl) {
        abrirOuNavegar(aba, approveUrl);
      } else if (aba) {
        aba.close();
      }
    });
  }

  onProcessarRegua() {
    this.store.dispatch(processarReguaCobranca());
  }
}
