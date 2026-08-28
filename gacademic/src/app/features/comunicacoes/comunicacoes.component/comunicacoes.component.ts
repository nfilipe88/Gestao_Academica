import { AsyncPipe, CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Actions, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { combineLatest, map, take } from 'rxjs';
import { carregarTurmas } from '../../../store/academico/academic.actions';
import { selectTurmas } from '../../../store/academico/academic.selector';
import { carregarAlunos } from '../../../store/alunos/alunos.actions';
import { selectAlunos } from '../../../store/alunos/alunos.selector';
import { selectPerfilAcesso } from '../../../store/auth/auth.selectors';
import { carregarComunicados, criarComunicado, criarComunicadoSucesso } from '../../../store/comunicacoes/comunicacoes.actions';
import { DESTINATARIOS_COMUNICADO, TIPOS_COMUNICADO } from '../../../store/comunicacoes/comunicacoes.models';
import { selectComunicacoesError, selectComunicados, selectPaginacaoComunicados } from '../../../store/comunicacoes/comunicacoes.selector';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';
import { abrirOuTransferirBlob } from '../../../core/utils/abrir-em-nova-aba';

@Component({
  selector: 'app-comunicacoes.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe, PaginacaoComponent],
  templateUrl: './comunicacoes.component.html',
  styleUrl: './comunicacoes.component.css',
})
export class ComunicacoesComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private http = inject(HttpClient);
  private actions$ = inject(Actions);

  readonly tiposComunicado = TIPOS_COMUNICADO;
  readonly destinatariosComunicado = DESTINATARIOS_COMUNICADO;

  erro$ = this.store.select(selectComunicacoesError);
  perfilAcesso$ = this.store.select(selectPerfilAcesso);
  turmas$ = this.store.select(selectTurmas);
  alunos$ = this.store.select(selectAlunos);
  paginacaoComunicados$ = this.store.select(selectPaginacaoComunicados);

  // Junta cada comunicado com o nome legível do destinatário (a API só
  // devolve o id da turma/aluno, não o nome).
  comunicados$ = combineLatest([
    this.store.select(selectComunicados),
    this.turmas$,
    this.alunos$
  ]).pipe(
    map(([comunicados, turmas, alunos]) => comunicados.map(c => ({
      ...c,
      destinatarioLabel:
        c.destinatario_tipo === 'TURMA' ? (turmas.find(t => t.id === c.destinatario_turma_id)?.nome_codigo ?? '—') :
        c.destinatario_tipo === 'ALUNO' ? (alunos.find(a => a.id === c.destinatario_aluno_id)?.nome_completo ?? '—') :
        'Toda a escola'
    })))
  );

  mostrarFormulario = false;
  ficheiroAnexo: File | null = null;

  comunicadoForm = this.fb.group({
    tipo: ['COMUNICADO', Validators.required],
    titulo: ['', Validators.required],
    corpo: ['', Validators.required],
    destinatario_tipo: ['TURMA', Validators.required],
    destinatario_turma_id: [''],
    destinatario_aluno_id: ['']
  });

  paginaComunicados = 1;
  tamanhoComunicados = 25;

  ngOnInit() {
    this.store.dispatch(carregarComunicados({ page: this.paginaComunicados, page_size: this.tamanhoComunicados }));
    // Precisamos das turmas e alunos para os <select> de destinatário e
    // para mostrar o nome de cada um na lista de histórico.
    this.store.dispatch(carregarTurmas());
    this.store.dispatch(carregarAlunos({ page_size: 100 })); // povoa um <select>, ver nota em transferencias.component.ts
  }

  onPaginaComunicados(pagina: number) {
    this.paginaComunicados = pagina;
    this.store.dispatch(carregarComunicados({ page: pagina, page_size: this.tamanhoComunicados }));
  }

  onTamanhoComunicados(tamanho: number) {
    this.tamanhoComunicados = tamanho;
    this.paginaComunicados = 1;
    this.store.dispatch(carregarComunicados({ page: 1, page_size: tamanho }));
  }

  alternarFormulario() {
    this.mostrarFormulario = !this.mostrarFormulario;
    this.comunicadoForm.reset({ tipo: 'COMUNICADO', destinatario_tipo: 'TURMA' });
    this.ficheiroAnexo = null;
  }

  onSelecionarAnexo(event: Event) {
    this.ficheiroAnexo = (event.target as HTMLInputElement).files?.[0] ?? null;
  }

  onSubmit() {
    if (this.comunicadoForm.invalid) return;
    const v = this.comunicadoForm.value;
    const ficheiro = this.ficheiroAnexo;

    // Só interessa o PRÓXIMO comunicado criado (take(1)) — é o que esta
    // submissão está prestes a disparar. Subscrito antes do dispatch
    // para não perder o evento por causa da ordem de execução.
    if (ficheiro) {
      this.actions$.pipe(ofType(criarComunicadoSucesso), take(1)).subscribe(({ comunicado }) => {
        const dados = new FormData();
        dados.append('ficheiro', ficheiro);
        this.http.put(`/api/v1/comunicados/${comunicado.id}/anexo`, dados).subscribe();
      });
    }

    this.store.dispatch(criarComunicado({
      tipo: v.tipo!,
      titulo: v.titulo!,
      corpo: v.corpo!,
      destinatario_tipo: v.destinatario_tipo!,
      destinatario_turma_id: v.destinatario_tipo === 'TURMA' ? (v.destinatario_turma_id || null) : null,
      destinatario_aluno_id: v.destinatario_tipo === 'ALUNO' ? (v.destinatario_aluno_id || null) : null
    }));
    this.comunicadoForm.reset({ tipo: 'COMUNICADO', destinatario_tipo: 'TURMA' });
    this.mostrarFormulario = false;
    this.ficheiroAnexo = null;
  }

  onDescarregarAnexo(comunicadoId: string) {
    const aba = window.open('', '_blank');
    this.http.get(`/api/v1/comunicados/${comunicadoId}/anexo`, { responseType: 'blob' }).subscribe({
      next: (blob) => abrirOuTransferirBlob(aba, blob, `anexo-${comunicadoId}`),
      error: () => { if (aba) aba.close(); }
    });
  }
}
