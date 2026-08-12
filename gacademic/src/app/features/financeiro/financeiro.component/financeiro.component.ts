import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { carregarAlunos } from '../../../store/alunos/alunos.actions';
import { selectAlunos } from '../../../store/alunos/alunos.selector';
import { selectIsGestorOuSecretaria } from '../../../store/auth/auth.selectors';
import {
  carregarContratoDaMatricula, carregarMatriculasDoAluno, carregarResponsaveisDaMatricula,
  criarContrato, marcarFaturaPaga, processarReguaCobranca
} from '../../../store/financeiro/financeiro.actions';
import {
  selectContrato, selectContratoCarregado, selectFaturas, selectFinanceiroError,
  selectFinanceiroMensagem, selectMatriculasDoAluno, selectResponsaveisElegiveis
} from '../../../store/financeiro/financeiro.selector';

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

  alunos$ = this.store.select(selectAlunos);
  matriculas$ = this.store.select(selectMatriculasDoAluno);
  responsaveis$ = this.store.select(selectResponsaveisElegiveis);
  contrato$ = this.store.select(selectContrato);
  contratoCarregado$ = this.store.select(selectContratoCarregado);
  faturas$ = this.store.select(selectFaturas);
  erro$ = this.store.select(selectFinanceiroError);
  mensagem$ = this.store.select(selectFinanceiroMensagem);
  podeGerir$ = this.store.select(selectIsGestorOuSecretaria);

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

  ngOnInit() {
    this.store.dispatch(carregarAlunos());
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

  onProcessarRegua() {
    this.store.dispatch(processarReguaCobranca());
  }
}
