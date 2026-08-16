import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnDestroy, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { combineLatest, debounceTime, distinctUntilChanged, map, Subscription } from 'rxjs';
import {
  carregarAlunos, carregarResponsaveis, carregarResponsaveisDoAluno,
  criarAcessoAluno, criarAcessoResponsavel, criarAluno, criarResponsavel, vincularResponsavel
} from '../../../store/alunos/alunos.actions';
import {
  selectAlunos, selectAlunosError, selectAlunosMensagem, selectPaginacaoAlunos,
  selectResponsaveis, selectVinculos
} from '../../../store/alunos/alunos.selector';
import { selectIsGestorOuSecretaria } from '../../../store/auth/auth.selectors';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';

@Component({
  selector: 'app-alunos.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe, PaginacaoComponent],
  templateUrl: './alunos.component.html',
  styleUrl: './alunos.component.css',
})
export class AlunosComponent implements OnInit, OnDestroy {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private subscricoes = new Subscription();

  erro$ = this.store.select(selectAlunosError);
  mensagem$ = this.store.select(selectAlunosMensagem);
  responsaveis$ = this.store.select(selectResponsaveis);
  paginacaoAlunos$ = this.store.select(selectPaginacaoAlunos);

  // Criar/editar alunos, responsáveis, vínculos e acessos ao Portal =
  // GESTOR ou SECRETARIA (ver _PODE_GERIR em alunos.py).
  podeGerir$ = this.store.select(selectIsGestorOuSecretaria);

  // Cada aluno já com os seus responsáveis vinculados (nome e usuario_id
  // resolvidos a partir de responsavel_id — a API só devolve o vínculo em si).
  alunos$ = combineLatest([
    this.store.select(selectAlunos),
    this.store.select(selectVinculos),
    this.responsaveis$
  ]).pipe(
    map(([alunos, vinculos, responsaveis]) => alunos.map(aluno => ({
      ...aluno,
      vinculos: vinculos
        .filter(v => v.aluno_id === aluno.id)
        .map(v => {
          const responsavel = responsaveis.find(r => r.id === v.responsavel_id);
          return {
            ...v,
            nomeResponsavel: responsavel?.nome_completo ?? '—',
            usuarioIdResponsavel: responsavel?.usuario_id ?? null
          };
        })
    })))
  );

  // Qual aluno/responsável está com o mini-formulário de "Criar acesso ao
  // Portal" aberto — só um de cada vez, identificado por "aluno:<id>" ou
  // "responsavel:<id>".
  acessoFormAbertoPara: string | null = null;
  acessoForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    palavra_passe: ['', [Validators.required, Validators.minLength(8)]]
  });

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

  // Página/tamanho atuais da tabela de Alunos, guardados aqui para os
  // reenviarmos ao criar um novo registo (o effect volta sempre à
  // página 1, mas se o utilizador tinha escolhido "50 por página" isso
  // deve manter-se).
  paginaAlunos = 1;
  tamanhoAlunos = 25;

  // Filtro por busca (nome/matrícula/documento) e por intervalo de data
  // de nascimento — combinado com a paginação já existente (ver
  // dispatchAlunosComFiltros). A busca tem debounce para não disparar
  // um pedido a cada tecla; as datas disparam logo (menos frequentes).
  filtroForm = this.fb.group({
    busca: [''],
    data_nascimento_inicio: [''],
    data_nascimento_fim: ['']
  });

  ngOnInit() {
    this.store.dispatch(carregarAlunos({ page: this.paginaAlunos, page_size: this.tamanhoAlunos }));
    // Responsáveis não tem tabela própria nesta página — só povoa o
    // <select> de "vincular responsável" — por isso pede o máximo
    // permitido (100) em vez de paginar (limitação conhecida para
    // escolas com mais de 100 responsáveis, ver nota em
    // transferencias.component.ts).
    this.store.dispatch(carregarResponsaveis({ page_size: 100 }));

    this.subscricoes.add(
      this.filtroForm.controls.busca.valueChanges.pipe(
        debounceTime(300),
        distinctUntilChanged()
      ).subscribe(() => this.aplicarFiltros())
    );
    this.subscricoes.add(
      this.filtroForm.controls.data_nascimento_inicio.valueChanges.subscribe(() => this.aplicarFiltros())
    );
    this.subscricoes.add(
      this.filtroForm.controls.data_nascimento_fim.valueChanges.subscribe(() => this.aplicarFiltros())
    );
  }

  ngOnDestroy() {
    this.subscricoes.unsubscribe();
  }

  private dispatchAlunosComFiltros(pagina: number) {
    const { busca, data_nascimento_inicio, data_nascimento_fim } = this.filtroForm.value;
    this.store.dispatch(carregarAlunos({
      page: pagina, page_size: this.tamanhoAlunos,
      busca: busca?.trim() || undefined,
      data_nascimento_inicio: data_nascimento_inicio || undefined,
      data_nascimento_fim: data_nascimento_fim || undefined
    }));
  }

  aplicarFiltros() {
    this.paginaAlunos = 1;
    this.dispatchAlunosComFiltros(1);
  }

  limparFiltros() {
    this.filtroForm.reset({ busca: '', data_nascimento_inicio: '', data_nascimento_fim: '' });
    this.aplicarFiltros();
  }

  onPaginaAlunos(pagina: number) {
    this.paginaAlunos = pagina;
    this.dispatchAlunosComFiltros(pagina);
  }

  onTamanhoAlunos(tamanho: number) {
    this.tamanhoAlunos = tamanho;
    this.paginaAlunos = 1;
    this.dispatchAlunosComFiltros(1);
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

  alternarFormularioAcesso(chave: string) {
    this.acessoFormAbertoPara = this.acessoFormAbertoPara === chave ? null : chave;
    this.acessoForm.reset();
  }

  onCriarAcessoAluno(alunoId: string) {
    if (this.acessoForm.invalid) return;
    const { email, palavra_passe } = this.acessoForm.value;
    this.store.dispatch(criarAcessoAluno({ aluno_id: alunoId, email: email!, palavra_passe: palavra_passe! }));
    this.acessoFormAbertoPara = null;
  }

  onCriarAcessoResponsavel(responsavelId: string) {
    if (this.acessoForm.invalid) return;
    const { email, palavra_passe } = this.acessoForm.value;
    this.store.dispatch(criarAcessoResponsavel({ responsavel_id: responsavelId, email: email!, palavra_passe: palavra_passe! }));
    this.acessoFormAbertoPara = null;
  }
}
