import { AsyncPipe, CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
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
import { AlunoDocumento, FotoPerfilAluno } from '../../../store/alunos/alunos.models';
import { abrirOuTransferirBlob } from '../../../core/utils/abrir-em-nova-aba';
import { selectIsGestorOuSecretaria } from '../../../store/auth/auth.selectors';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';
import { carregarTurmas } from '../../../store/academico/academic.actions';
import { selectTurmas } from '../../../store/academico/academic.selector';
import { MatriculaResumo } from '../../../store/financeiro/financeiro.models';

@Component({
  selector: 'app-alunos.component',
  imports: [ReactiveFormsModule, FormsModule, CommonModule, AsyncPipe, PaginacaoComponent],
  templateUrl: './alunos.component.html',
  styleUrl: './alunos.component.css',
})
export class AlunosComponent implements OnInit, OnDestroy {
  private fb = inject(FormBuilder);
  private store = inject(Store);
  private http = inject(HttpClient);
  private subscricoes = new Subscription();

  erro$ = this.store.select(selectAlunosError);
  mensagem$ = this.store.select(selectAlunosMensagem);
  responsaveis$ = this.store.select(selectResponsaveis);
  paginacaoAlunos$ = this.store.select(selectPaginacaoAlunos);

  // Turmas para o <select> de "Matricular" (secção Matrícula, dentro
  // do painel expandido de cada aluno) — mesma store já usada por
  // features/academico/turmas.component.ts.
  turmas$ = this.store.select(selectTurmas);

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

  matricularAlunoForm = this.fb.group({
    turma_id: ['', Validators.required],
    ano_letivo: [new Date().getFullYear(), [Validators.required, Validators.min(2000)]]
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
    // Povoa o <select> de "Matricular" na secção Matrícula de cada
    // aluno — mesmo dispatch já feito por turmas.component.ts.
    this.store.dispatch(carregarTurmas());

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

  // ==========================================
  // MATRÍCULA (descoberta a partir do próprio Aluno) — antes disto, a
  // única forma de matricular um aluno era ir a Turmas → "Ver alunos"
  // → escolhê-lo num <select>, sem nenhuma pista aqui em Alunos a
  // apontar para lá (achado real de uma auditoria de UX desta sessão).
  // Mesmo endpoint (POST /api/v1/matriculas) e mesmo padrão de "pequeno
  // de mais para um slice próprio" de Documentos/Foto de Perfil abaixo
  // — só o GET de leitura (/alunos/{id}/matriculas) já existia,
  // reaproveitado de store/financeiro (usado lá para o <select> de
  // "Matrícula/Ano letivo" da página Financeiro).
  // ==========================================
  alunoMatriculasAbertoId = signal<string | null>(null);
  matriculasPorAluno = signal<Record<string, MatriculaResumo[]>>({});
  aMatricularAlunoId = signal<string | null>(null);
  erroMatricularAluno = signal<string | null>(null);

  private recarregarMatriculasDoAluno(alunoId: string) {
    this.http.get<MatriculaResumo[]>(`/api/v1/alunos/${alunoId}/matriculas`).subscribe({
      next: (matriculas) => this.matriculasPorAluno.update(atual => ({ ...atual, [alunoId]: matriculas })),
    });
  }

  onAlternarMatriculas(alunoId: string) {
    const abrir = this.alunoMatriculasAbertoId() !== alunoId;
    this.alunoMatriculasAbertoId.set(abrir ? alunoId : null);
    this.matricularAlunoForm.reset({ turma_id: '', ano_letivo: new Date().getFullYear() });
    this.erroMatricularAluno.set(null);
    if (abrir) this.recarregarMatriculasDoAluno(alunoId);
  }

  onMatricularAluno(alunoId: string) {
    if (this.matricularAlunoForm.invalid) return;
    const { turma_id, ano_letivo } = this.matricularAlunoForm.value;
    this.aMatricularAlunoId.set(alunoId);
    this.erroMatricularAluno.set(null);
    this.http.post(`/api/v1/matriculas`, { aluno_id: alunoId, turma_id, ano_letivo }).subscribe({
      next: () => {
        this.aMatricularAlunoId.set(null);
        this.matricularAlunoForm.reset({ turma_id: '', ano_letivo: new Date().getFullYear() });
        this.recarregarMatriculasDoAluno(alunoId);
      },
      error: (err) => {
        this.aMatricularAlunoId.set(null);
        this.erroMatricularAluno.set(err.error?.detail || 'Não foi possível matricular o aluno.');
      },
    });
  }

  // ==========================================
  // DOCUMENTOS DO ALUNO (sobretudo Histórico Escolar automático de
  // Transferência/Reingresso) — pequeno de mais para justificar um
  // slice de NgRx próprio, mesmo padrão de MatriculaDocumento em
  // turmas.component.ts.
  // ==========================================
  alunoDocumentosAbertoId = signal<string | null>(null);
  documentosPorAluno = signal<Record<string, AlunoDocumento[]>>({});
  descricaoDocumentoPorAluno: Record<string, string> = {};
  documentoAEnviarAlunoId = signal<string | null>(null);

  onAlternarDocumentos(alunoId: string) {
    const abrir = this.alunoDocumentosAbertoId() !== alunoId;
    this.alunoDocumentosAbertoId.set(abrir ? alunoId : null);
    if (abrir) {
      this.http.get<AlunoDocumento[]>(`/api/v1/alunos/${alunoId}/documentos`).subscribe({
        next: (documentos) => this.documentosPorAluno.update(atual => ({ ...atual, [alunoId]: documentos })),
      });
    }
  }

  onSelecionarDocumento(evento: Event, alunoId: string) {
    const ficheiro = (evento.target as HTMLInputElement).files?.[0];
    if (!ficheiro) return;
    const dados = new FormData();
    dados.append('ficheiro', ficheiro);
    const descricao = this.descricaoDocumentoPorAluno[alunoId] || '';
    this.documentoAEnviarAlunoId.set(alunoId);
    this.http.post<{ documentos: AlunoDocumento[] }>(
      `/api/v1/alunos/${alunoId}/documentos?descricao=${encodeURIComponent(descricao)}`, dados
    ).subscribe({
      next: (resp) => {
        this.documentoAEnviarAlunoId.set(null);
        this.documentosPorAluno.update(atual => ({ ...atual, [alunoId]: resp.documentos }));
        this.descricaoDocumentoPorAluno[alunoId] = '';
      },
      error: () => this.documentoAEnviarAlunoId.set(null),
    });
    (evento.target as HTMLInputElement).value = '';
  }

  onRemoverDocumento(alunoId: string, documentoId: string) {
    this.http.delete<{ documentos: AlunoDocumento[] }>(
      `/api/v1/alunos/${alunoId}/documentos/${documentoId}`
    ).subscribe({
      next: (resp) => this.documentosPorAluno.update(atual => ({ ...atual, [alunoId]: resp.documentos })),
    });
  }

  onVerDocumento(alunoId: string, documentoId: string) {
    const janela = window.open('', '_blank');
    this.http.get<{ url: string }>(`/api/v1/alunos/${alunoId}/documentos/${documentoId}/url`).subscribe({
      next: (resp) => {
        janela?.document.write(`<iframe src="${resp.url}" style="border:0;position:fixed;inset:0;width:100%;height:100%"></iframe>`);
      },
      error: () => janela?.close(),
    });
  }

  // ==========================================
  // FOTO DE PERFIL (a que vale para o cartão de acesso — ver
  // app/database/models_pessoas.py::FotoPerfilAluno). Mesmo padrão do
  // painel de Documentos acima: pequeno de mais para um slice próprio.
  // ==========================================
  alunoFotosAbertoId = signal<string | null>(null);
  fotosPorAluno = signal<Record<string, FotoPerfilAluno[]>>({});
  fotoAEnviarAlunoId = signal<string | null>(null);

  onAlternarFotos(alunoId: string) {
    const abrir = this.alunoFotosAbertoId() !== alunoId;
    this.alunoFotosAbertoId.set(abrir ? alunoId : null);
    if (abrir) {
      this.http.get<FotoPerfilAluno[]>(`/api/v1/alunos/${alunoId}/fotos-perfil`).subscribe({
        next: (fotos) => this.fotosPorAluno.update(atual => ({ ...atual, [alunoId]: fotos })),
      });
    }
  }

  onSelecionarFoto(evento: Event, alunoId: string) {
    const ficheiro = (evento.target as HTMLInputElement).files?.[0];
    if (!ficheiro) return;
    const dados = new FormData();
    dados.append('ficheiro', ficheiro);
    this.fotoAEnviarAlunoId.set(alunoId);
    this.http.post<{ fotos: FotoPerfilAluno[] }>(`/api/v1/alunos/${alunoId}/foto-perfil`, dados).subscribe({
      next: (resp) => {
        this.fotoAEnviarAlunoId.set(null);
        this.fotosPorAluno.update(atual => ({ ...atual, [alunoId]: resp.fotos }));
      },
      error: () => this.fotoAEnviarAlunoId.set(null),
    });
    (evento.target as HTMLInputElement).value = '';
  }

  onVerFoto(alunoId: string, fotoId: string) {
    const janela = window.open('', '_blank');
    this.http.get<{ url: string }>(`/api/v1/alunos/${alunoId}/fotos-perfil/${fotoId}/url`).subscribe({
      next: (resp) => {
        janela?.document.write(`<img src="${resp.url}" style="max-width:100%;max-height:100vh;display:block;margin:0 auto">`);
      },
      error: () => janela?.close(),
    });
  }

  onVerCartaoAcesso(alunoId: string) {
    const aba = window.open('', '_blank');
    this.http.get(`/api/v1/alunos/${alunoId}/cartao-acesso.pdf`, { responseType: 'blob' }).subscribe({
      next: (blob) => abrirOuTransferirBlob(aba, blob, `cartao-acesso-${alunoId}.pdf`),
      error: () => { if (aba) aba.close(); }
    });
  }
}
