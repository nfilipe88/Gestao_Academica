import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { combineLatest, map, startWith } from 'rxjs';
import {
  adicionarDisciplinaASerie, carregarCursos, carregarDisciplinas, carregarGradeCurricular,
  carregarObjetivosAprendizagem, carregarSeries, criarCurso, criarDisciplina, criarObjetivoAprendizagem, criarSerieAno
} from '../../../../store/academico/academic.actions';
import {
  selectAcademicoError, selectCursos, selectDisciplinas, selectGradeCurricular, selectObjetivosAprendizagem, selectSeries
} from '../../../../store/academico/academic.selector';
import { ObjetivoAprendizagem } from '../../../../store/academico/academic.models';
import { selectIsGestorOuSecretaria } from '../../../../store/auth/auth.selectors';

@Component({
  selector: 'app-cursos.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe],
  templateUrl: './cursos.component.html',
  styleUrl: './cursos.component.css',
})
export class CursosComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  erro$ = this.store.select(selectAcademicoError);
  disciplinas$ = this.store.select(selectDisciplinas);
  objetivos$ = this.store.select(selectObjetivosAprendizagem);

  // Criar/editar cursos, séries, grade curricular e disciplinas =
  // GESTOR ou SECRETARIA (ver _PODE_GERIR em academico.py).
  podeGerir$ = this.store.select(selectIsGestorOuSecretaria);

  // Cada curso já com as suas Séries/Anos agrupadas, e cada série já com
  // as suas disciplinas (grade curricular) — tudo junto aqui no cliente,
  // já que a API devolve cada entidade separada.
  private cursosComSeries$ = combineLatest([
    this.store.select(selectCursos),
    this.store.select(selectSeries),
    this.store.select(selectGradeCurricular),
    this.disciplinas$
  ]).pipe(
    map(([cursos, series, grade, disciplinas]) => cursos.map(curso => ({
      ...curso,
      series: series
        .filter(serie => serie.curso_id === curso.id)
        .map(serie => ({
          ...serie,
          disciplinas: grade
            .filter(g => g.serie_ano_id === serie.id)
            .map(g => disciplinas.find(d => d.id === g.disciplina_id)?.nome ?? '—')
        }))
    })))
  );

  // Busca por nome — ambas as tabelas desta página (Cursos e
  // Disciplinas) já carregam tudo de uma vez, por isso o filtro é só
  // no cliente, sem novo pedido ao back-end.
  filtroCursos = this.fb.group({ busca: [''] });
  filtroDisciplinas = this.fb.group({ busca: [''] });

  cursos$ = combineLatest([
    this.cursosComSeries$,
    this.filtroCursos.valueChanges.pipe(startWith(this.filtroCursos.value))
  ]).pipe(
    map(([cursos, filtro]) => !filtro.busca
      ? cursos
      : cursos.filter(c => c.nome.toLowerCase().includes(filtro.busca!.trim().toLowerCase()))
    )
  );

  disciplinasFiltradas$ = combineLatest([
    this.disciplinas$,
    this.filtroDisciplinas.valueChanges.pipe(startWith(this.filtroDisciplinas.value))
  ]).pipe(
    map(([disciplinas, filtro]) => !filtro.busca
      ? disciplinas
      : disciplinas.filter(d => d.nome.toLowerCase().includes(filtro.busca!.trim().toLowerCase()))
    )
  );

  // Qual curso está com o painel de Séries/Anos aberto (só um de cada vez).
  cursoExpandidoId: string | null = null;
  // Qual série (dentro do curso aberto) está com o painel de Disciplinas aberto.
  serieExpandidaId: string | null = null;

  mostrarFormulario = false;
  mostrarFormularioDisciplina = false;

  cursoForm = this.fb.group({
    nome: ['', Validators.required]
  });

  serieForm = this.fb.group({
    nome: ['', Validators.required]
  });

  disciplinaForm = this.fb.group({
    nome: ['', Validators.required],
    carga_horaria_total: ['']
  });

  gradeForm = this.fb.group({
    disciplina_id: ['', Validators.required]
  });

  // Qual disciplina (na tabela "Disciplinas" no fundo da página) está
  // com o painel de Objetivos de Aprendizagem aberto (só uma de cada vez).
  disciplinaExpandidaId: string | null = null;
  objetivoForm = this.fb.group({
    nome: ['', Validators.required],
    descricao: ['']
  });

  ngOnInit() {
    // Ao abrir o ecrã, pede à Store para ir buscar os dados ao Back-end
    this.store.dispatch(carregarCursos());
    this.store.dispatch(carregarSeries());
    this.store.dispatch(carregarDisciplinas());
    this.store.dispatch(carregarGradeCurricular());
    this.store.dispatch(carregarObjetivosAprendizagem({}));
  }

  alternarFormulario() {
    this.mostrarFormulario = !this.mostrarFormulario;
    this.cursoForm.reset();
  }

  onSubmit() {
    if (this.cursoForm.valid) {
      this.store.dispatch(criarCurso({ nome: this.cursoForm.value.nome! }));
      this.cursoForm.reset();
      this.mostrarFormulario = false;
    }
  }

  alternarExpandido(cursoId: string) {
    this.cursoExpandidoId = this.cursoExpandidoId === cursoId ? null : cursoId;
    this.serieExpandidaId = null;
    this.serieForm.reset();
  }

  onSubmitSerie(cursoId: string) {
    if (this.serieForm.valid) {
      this.store.dispatch(criarSerieAno({ curso_id: cursoId, nome: this.serieForm.value.nome! }));
      this.serieForm.reset();
    }
  }

  alternarSerieExpandida(serieId: string) {
    this.serieExpandidaId = this.serieExpandidaId === serieId ? null : serieId;
    this.gradeForm.reset();
  }

  onSubmitGrade(serieId: string) {
    if (this.gradeForm.valid) {
      this.store.dispatch(adicionarDisciplinaASerie({
        serie_ano_id: serieId,
        disciplina_id: this.gradeForm.value.disciplina_id!
      }));
      this.gradeForm.reset();
    }
  }

  alternarFormularioDisciplina() {
    this.mostrarFormularioDisciplina = !this.mostrarFormularioDisciplina;
    this.disciplinaForm.reset();
  }

  onSubmitDisciplina() {
    if (this.disciplinaForm.valid) {
      const { nome, carga_horaria_total } = this.disciplinaForm.value;
      this.store.dispatch(criarDisciplina({
        nome: nome!,
        carga_horaria_total: carga_horaria_total ? Number(carga_horaria_total) : null
      }));
      this.disciplinaForm.reset();
      this.mostrarFormularioDisciplina = false;
    }
  }

  alternarDisciplinaExpandida(disciplinaId: string) {
    this.disciplinaExpandidaId = this.disciplinaExpandidaId === disciplinaId ? null : disciplinaId;
    this.objetivoForm.reset();
  }

  objetivosDaDisciplina(objetivos: ObjetivoAprendizagem[] | null, disciplinaId: string): ObjetivoAprendizagem[] {
    if (!objetivos) return [];
    return objetivos.filter(o => o.disciplina_id === disciplinaId);
  }

  onSubmitObjetivo(disciplinaId: string) {
    if (this.objetivoForm.invalid) return;
    const { nome, descricao } = this.objetivoForm.value;
    this.store.dispatch(criarObjetivoAprendizagem({
      disciplina_id: disciplinaId,
      nome: nome!,
      descricao: descricao || null
    }));
    this.objetivoForm.reset();
  }
}
