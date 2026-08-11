import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { combineLatest, map } from 'rxjs';
import { carregarTurmas } from '../../../store/academico/academic.actions';
import { selectTurmas } from '../../../store/academico/academic.selector';
import { carregarAlunos } from '../../../store/alunos/alunos.actions';
import { selectAlunos } from '../../../store/alunos/alunos.selector';
import { selectPerfilAcesso } from '../../../store/auth/auth.selectors';
import { carregarComunicados, criarComunicado } from '../../../store/comunicacoes/comunicacoes.actions';
import { DESTINATARIOS_COMUNICADO, TIPOS_COMUNICADO } from '../../../store/comunicacoes/comunicacoes.models';
import { selectComunicacoesError, selectComunicados } from '../../../store/comunicacoes/comunicacoes.selector';

@Component({
  selector: 'app-comunicacoes.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe],
  templateUrl: './comunicacoes.component.html',
  styleUrl: './comunicacoes.component.css',
})
export class ComunicacoesComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  readonly tiposComunicado = TIPOS_COMUNICADO;
  readonly destinatariosComunicado = DESTINATARIOS_COMUNICADO;

  erro$ = this.store.select(selectComunicacoesError);
  perfilAcesso$ = this.store.select(selectPerfilAcesso);
  turmas$ = this.store.select(selectTurmas);
  alunos$ = this.store.select(selectAlunos);

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

  comunicadoForm = this.fb.group({
    tipo: ['COMUNICADO', Validators.required],
    titulo: ['', Validators.required],
    corpo: ['', Validators.required],
    destinatario_tipo: ['TURMA', Validators.required],
    destinatario_turma_id: [''],
    destinatario_aluno_id: ['']
  });

  ngOnInit() {
    this.store.dispatch(carregarComunicados());
    // Precisamos das turmas e alunos para os <select> de destinatário e
    // para mostrar o nome de cada um na lista de histórico.
    this.store.dispatch(carregarTurmas());
    this.store.dispatch(carregarAlunos());
  }

  alternarFormulario() {
    this.mostrarFormulario = !this.mostrarFormulario;
    this.comunicadoForm.reset({ tipo: 'COMUNICADO', destinatario_tipo: 'TURMA' });
  }

  onSubmit() {
    if (this.comunicadoForm.invalid) return;
    const v = this.comunicadoForm.value;
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
  }
}
