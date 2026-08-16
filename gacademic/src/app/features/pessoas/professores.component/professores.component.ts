import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { combineLatest, debounceTime, distinctUntilChanged, map, Subscription } from 'rxjs';
import { carregarCursos, carregarDisciplinas, carregarSeries, carregarTurmas } from '../../../store/academico/academic.actions';
import { selectDisciplinas, selectTurmas } from '../../../store/academico/academic.selector';
import { selectIsGestor, selectIsGestorOuSecretaria } from '../../../store/auth/auth.selectors';
import { carregarAlocacoes, carregarProfessores, criarAlocacao, criarProfessor } from '../../../store/professores/professores.actions';
import { selectAlocacoes, selectPaginacaoProfessores, selectProfessores, selectProfessoresError } from '../../../store/professores/professores.selector';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';

@Component({
  selector: 'app-professores.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe, PaginacaoComponent],
  templateUrl: './professores.component.html',
  styleUrl: './professores.component.css',
})
export class ProfessoresComponent implements OnInit, OnDestroy {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private subscricoes = new Subscription();

  erro$ = this.store.select(selectProfessoresError);
  turmas$ = this.store.select(selectTurmas);
  disciplinas$ = this.store.select(selectDisciplinas);
  paginacaoProfessores$ = this.store.select(selectPaginacaoProfessores);

  // Criar conta de professor = GESTOR apenas (ver POST /professores no
  // back-end); alocar a turma/disciplina = GESTOR ou SECRETARIA.
  podeGerir$ = this.store.select(selectIsGestor);
  podeAlocar$ = this.store.select(selectIsGestorOuSecretaria);

  // Cada professor já com as suas alocações (turma + disciplina) juntas.
  professores$ = combineLatest([
    this.store.select(selectProfessores),
    this.store.select(selectAlocacoes)
  ]).pipe(
    map(([professores, alocacoes]) => professores.map(professor => ({
      ...professor,
      alocacoes: alocacoes.filter(a => a.professor_id === professor.id)
    })))
  );

  mostrarFormulario = false;
  professorExpandidoId: string | null = null;

  professorForm = this.fb.group({
    nome_completo: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    palavra_passe: ['', [Validators.required, Validators.minLength(8)]],
    formacao_academica: ['']
  });

  alocarForm = this.fb.group({
    turma_id: ['', Validators.required],
    disciplina_id: ['', Validators.required]
  });

  paginaProfessores = 1;
  tamanhoProfessores = 25;

  // Busca por nome/e-mail — debounce para não disparar um pedido a
  // cada tecla (mesmo padrão do filtro de Alunos).
  filtroForm = this.fb.group({ busca: [''] });

  ngOnInit() {
    this.store.dispatch(carregarProfessores({ page: this.paginaProfessores, page_size: this.tamanhoProfessores }));
    this.store.dispatch(carregarAlocacoes());
    // Precisamos das turmas e disciplinas para os <select> de alocação.
    this.store.dispatch(carregarTurmas());
    this.store.dispatch(carregarDisciplinas());
    this.store.dispatch(carregarCursos());
    this.store.dispatch(carregarSeries());

    this.subscricoes.add(
      this.filtroForm.controls.busca.valueChanges.pipe(
        debounceTime(300),
        distinctUntilChanged()
      ).subscribe(() => {
        this.paginaProfessores = 1;
        this.dispatchProfessoresComFiltro(1);
      })
    );
  }

  ngOnDestroy() {
    this.subscricoes.unsubscribe();
  }

  private dispatchProfessoresComFiltro(pagina: number) {
    this.store.dispatch(carregarProfessores({
      page: pagina, page_size: this.tamanhoProfessores,
      busca: this.filtroForm.value.busca?.trim() || undefined
    }));
  }

  limparFiltro() {
    this.filtroForm.reset({ busca: '' });
    this.paginaProfessores = 1;
    this.dispatchProfessoresComFiltro(1);
  }

  onPaginaProfessores(pagina: number) {
    this.paginaProfessores = pagina;
    this.dispatchProfessoresComFiltro(pagina);
  }

  onTamanhoProfessores(tamanho: number) {
    this.tamanhoProfessores = tamanho;
    this.paginaProfessores = 1;
    this.dispatchProfessoresComFiltro(1);
  }

  alternarFormulario() {
    this.mostrarFormulario = !this.mostrarFormulario;
    this.professorForm.reset();
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
    this.mostrarFormulario = false;
  }

  alternarExpandido(professorId: string) {
    this.professorExpandidoId = this.professorExpandidoId === professorId ? null : professorId;
    this.alocarForm.reset();
  }

  onAlocar(professorId: string) {
    if (this.alocarForm.invalid) return;
    const { turma_id, disciplina_id } = this.alocarForm.value;
    this.store.dispatch(criarAlocacao({
      professor_id: professorId,
      turma_id: turma_id!,
      disciplina_id: disciplina_id!
    }));
    this.alocarForm.reset();
  }
}
