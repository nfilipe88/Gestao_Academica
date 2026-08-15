import { AsyncPipe, DatePipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import { carregarAlunos } from '../../../store/alunos/alunos.actions';
import { selectAlunos } from '../../../store/alunos/alunos.selector';
import * as TransferenciasActions from '../../../store/transferencias/transferencias.actions';
import {
  selectSolicitacoesTransferencia, selectTransferenciasError, selectTransferenciasMensagem
} from '../../../store/transferencias/transferencias.selector';

@Component({
  selector: 'app-transferencias.component',
  imports: [AsyncPipe, DatePipe, FormsModule],
  templateUrl: './transferencias.component.html',
  styleUrl: './transferencias.component.css',
})
export class TransferenciasComponent implements OnInit {
  private store = inject(Store);

  alunos$ = this.store.select(selectAlunos);
  solicitacoes$ = this.store.select(selectSolicitacoesTransferencia);
  mensagem$ = this.store.select(selectTransferenciasMensagem);
  erro$ = this.store.select(selectTransferenciasError);

  mostrarFormulario = false;
  novoAlunoId = '';
  novoNifDestino = '';
  novoMotivo = '';

  ngOnInit() {
    this.store.dispatch(TransferenciasActions.carregarMinhasSolicitacoes());
    // page_size no máximo permitido (100): isto povoa um <select>, não
    // uma tabela paginada — uma escola com mais de 100 alunos só vê os
    // 100 primeiros aqui (limitação conhecida, fora do âmbito desta
    // passagem; precisaria de um combo com pesquisa/autocomplete).
    this.store.dispatch(carregarAlunos({ page_size: 100 }));
  }

  onSubmit() {
    if (!this.novoAlunoId || !this.novoNifDestino.trim()) return;
    this.store.dispatch(TransferenciasActions.criarSolicitacao({
      aluno_id: this.novoAlunoId, nif_destino: this.novoNifDestino.trim(), motivo: this.novoMotivo || undefined,
    }));
    this.mostrarFormulario = false;
    this.novoAlunoId = '';
    this.novoNifDestino = '';
    this.novoMotivo = '';
  }
}
