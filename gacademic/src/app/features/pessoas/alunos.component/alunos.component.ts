import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { combineLatest, map } from 'rxjs';
import {
  carregarAlunos, carregarResponsaveis, carregarResponsaveisDoAluno,
  criarAluno, criarResponsavel, vincularResponsavel
} from '../../../store/alunos/alunos.actions';
import { selectAlunos, selectAlunosError, selectResponsaveis, selectVinculos } from '../../../store/alunos/alunos.selector';

@Component({
  selector: 'app-alunos.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe],
  templateUrl: './alunos.component.html',
  styleUrl: './alunos.component.css',
})
export class AlunosComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  erro$ = this.store.select(selectAlunosError);
  responsaveis$ = this.store.select(selectResponsaveis);

  // Cada aluno já com os seus responsáveis vinculados (nome resolvido a
  // partir de responsavel_id — a API só devolve o vínculo em si).
  alunos$ = combineLatest([
    this.store.select(selectAlunos),
    this.store.select(selectVinculos),
    this.responsaveis$
  ]).pipe(
    map(([alunos, vinculos, responsaveis]) => alunos.map(aluno => ({
      ...aluno,
      vinculos: vinculos
        .filter(v => v.aluno_id === aluno.id)
        .map(v => ({
          ...v,
          nomeResponsavel: responsaveis.find(r => r.id === v.responsavel_id)?.nome_completo ?? '—'
        }))
    })))
  );

  // Qual aluno está com o painel de Responsáveis aberto (só um de cada vez).
  alunoExpandidoId: string | null = null;

  mostrarFormularioAluno = false;
  mostrarFormularioResponsavel = false;

  alunoForm = this.fb.group({
    matricula_interna: ['', Validators.required],
    nome_completo: ['', Validators.required],
    data_nascimento: ['', Validators.required],
    numero_documento: ['']
  });

  responsavelForm = this.fb.group({
    nome_completo: ['', Validators.required],
    telefone_contato: ['', Validators.required],
    numero_documento: [''],
    email: ['', Validators.email]
  });

  vincularForm = this.fb.group({
    responsavel_id: ['', Validators.required],
    tipo_parentesco: ['', Validators.required],
    responsavel_financeiro: [false]
  });

  ngOnInit() {
    this.store.dispatch(carregarAlunos());
    this.store.dispatch(carregarResponsaveis());
  }

  alternarFormularioAluno() {
    this.mostrarFormularioAluno = !this.mostrarFormularioAluno;
    this.alunoForm.reset();
  }

  onSubmitAluno() {
    if (this.alunoForm.invalid) return;
    const { matricula_interna, nome_completo, data_nascimento, numero_documento } = this.alunoForm.value;
    this.store.dispatch(criarAluno({
      matricula_interna: matricula_interna!,
      nome_completo: nome_completo!,
      data_nascimento: data_nascimento!,
      numero_documento: numero_documento || null
    }));
    this.alunoForm.reset();
    this.mostrarFormularioAluno = false;
  }

  alternarFormularioResponsavel() {
    this.mostrarFormularioResponsavel = !this.mostrarFormularioResponsavel;
    this.responsavelForm.reset();
  }

  onSubmitResponsavel() {
    if (this.responsavelForm.invalid) return;
    const { nome_completo, telefone_contato, numero_documento, email } = this.responsavelForm.value;
    this.store.dispatch(criarResponsavel({
      nome_completo: nome_completo!,
      telefone_contato: telefone_contato!,
      numero_documento: numero_documento || null,
      email: email || null
    }));
    this.responsavelForm.reset();
    this.mostrarFormularioResponsavel = false;
  }

  alternarExpandido(alunoId: string) {
    this.alunoExpandidoId = this.alunoExpandidoId === alunoId ? null : alunoId;
    this.vincularForm.reset({ responsavel_financeiro: false });
    if (this.alunoExpandidoId) {
      this.store.dispatch(carregarResponsaveisDoAluno({ aluno_id: this.alunoExpandidoId }));
    }
  }

  onVincular(alunoId: string) {
    if (this.vincularForm.invalid) return;
    const { responsavel_id, tipo_parentesco, responsavel_financeiro } = this.vincularForm.value;
    this.store.dispatch(vincularResponsavel({
      aluno_id: alunoId,
      responsavel_id: responsavel_id!,
      tipo_parentesco: tipo_parentesco!,
      responsavel_financeiro: !!responsavel_financeiro
    }));
    this.vincularForm.reset({ responsavel_financeiro: false });
  }
}
