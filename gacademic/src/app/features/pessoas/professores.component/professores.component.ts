import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { carregarProfessores, criarProfessor } from '../../../store/professores/professores.actions';
import { selectProfessores, selectProfessoresError } from '../../../store/professores/professores.selector';

@Component({
  selector: 'app-professores.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe],
  templateUrl: './professores.component.html',
  styleUrl: './professores.component.css',
})
export class ProfessoresComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  erro$ = this.store.select(selectProfessoresError);
  professores$ = this.store.select(selectProfessores);

  professorForm = this.fb.group({
    nome_completo: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    palavra_passe: ['', [Validators.required, Validators.minLength(8)]],
    formacao_academica: ['']
  });

  ngOnInit() {
    this.store.dispatch(carregarProfessores());
  }

  onSubmit() {
    if (this.professorForm.invalid) return;
    const { nome_completo, email, palavra_passe, formacao_academica } = this.professorForm.value;
    this.store.dispatch(criarProfessor({
      nome_completo: nome_completo!,
      email: email!,
      palavra_passe: palavra_passe!,
      formacao_academica: formacao_academica || null
    }));
    this.professorForm.reset();
  }
}
