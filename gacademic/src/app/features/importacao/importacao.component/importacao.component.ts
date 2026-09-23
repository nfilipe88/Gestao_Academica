import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Curso, Disciplina, SerieAno, Turma } from '../../../store/academico/academic.models';

// Tipos alinhados com app/schemas/importacao.py.
interface NotaTrimestre {
  mact: number | null;
  pt: number | null;
}

interface TrimestreDetectado {
  nome: string;
  tem_dados: boolean;
  formula_mt_original: string | null;
  peso_mact: number;
  peso_pt: number;
  peso_detectado_automaticamente: boolean;
}

interface AlunoDetectado {
  linha_excel: number;
  numero_pauta: number | null;
  nome_completo: string;
  aluno_existente_id: string | null;
  notas: Record<string, NotaTrimestre>;
  anomalias: string[];
}

interface MetadadosDetectados {
  disciplina_nome: string | null;
  sala: string | null;
  turma_nome_codigo: string | null;
  turno: string | null;
  ano_letivo_raw: string | null;
  ano_letivo: number | null;
  chave_storage_ficheiro: string;
}

interface PreviewResposta {
  metadados: MetadadosDetectados;
  trimestres: TrimestreDetectado[];
  alunos: AlunoDetectado[];
  resumo: { total_linhas: number; total_com_anomalias: number; total_correspondencias_nome_existente: number };
}

type AcaoAluno = 'CRIAR_NOVO_ALUNO' | 'REUTILIZAR_ALUNO_EXISTENTE';

interface AlunoConfirmado {
  nome_completo: string;
  acao: AcaoAluno;
  aluno_existente_id: string | null;
  notas: Record<string, NotaTrimestre>;
}

interface ImportacaoResposta {
  lote_importacao_id: string;
  estado: string;
  resumo: { total_alunos_criados: number; total_alunos_reaproveitados: number; total_notas_lancadas: number };
  alunos_com_data_nascimento_pendente: string[];
}

interface LoteHistorico {
  id: string;
  nome_ficheiro_original: string;
  ano_letivo: number;
  total_alunos_criados: number;
  total_alunos_reaproveitados: number;
  total_notas_lancadas: number;
  estado: string;
  data_criacao: string;
}

// Estado local de resolução de uma entidade partilhada (Curso/Série/
// Turma/Disciplina) — "existente" usa o id escolhido num <select>,
// "novo" usa o nome livre digitado; nunca os dois ao mesmo tempo (ver
// EntidadeRefOuNova no back-end).
interface EntidadeEdicao {
  modo: 'existente' | 'novo';
  id: string;
  nomeNovo: string;
}

function novaEntidadeEdicao(nomeNovo = ''): EntidadeEdicao {
  return { modo: 'novo', id: '', nomeNovo };
}

/**
 * Assistente de Importação de Dados Legados (mini-pauta MININED) — uma
 * escola que já funciona em papel/Excel carrega um ficheiro por turma+
 * disciplina e a plataforma regista o plantel, a matrícula e as notas
 * do trimestre em curso, reaproveitando o motor de avaliação já
 * existente (Diário de Classe).
 *
 * Mesmo idioma de matricula-wizard.component: HttpClient direto +
 * signals por passo, sem NgRx — é um assistente descartável de uma só
 * vez (ao contrário de eventos/crm, que são ecrãs de lista
 * persistentes). O preview (Passo 1→2) não grava nada na BD — só a
 * confirmação final (Passo 3→4) cria tudo de uma vez.
 */
@Component({
  selector: 'app-importacao.component',
  imports: [CommonModule, FormsModule],
  templateUrl: './importacao.component.html',
  styleUrl: './importacao.component.css',
})
export class ImportacaoComponent implements OnInit {
  private http = inject(HttpClient);

  passoAtual = signal<1 | 2 | 3 | 4>(1);
  ficheiroSelecionado = signal<File | null>(null);
  aProcessar = signal(false);
  erro = signal<string | null>(null);

  preview = signal<PreviewResposta | null>(null);

  // Passo 2 — metadados/entidades/pesos, todos editáveis.
  cursoEdicao = signal<EntidadeEdicao>(novaEntidadeEdicao());
  serieEdicao = signal<EntidadeEdicao>(novaEntidadeEdicao());
  turmaEdicao = signal<EntidadeEdicao>(novaEntidadeEdicao());
  disciplinaEdicao = signal<EntidadeEdicao>(novaEntidadeEdicao());
  anoLetivoEditado = signal<number | null>(null);
  trimestresEditados = signal<TrimestreDetectado[]>([]);

  // Catálogos para o modo "existente" dos <select> acima.
  cursos = signal<Curso[]>([]);
  series = signal<SerieAno[]>([]);
  turmas = signal<Turma[]>([]);
  disciplinas = signal<Disciplina[]>([]);

  // Passo 3 — plantel, com a ação (criar/reutilizar) editável por linha.
  alunosEditados = signal<AlunoConfirmado[]>([]);

  resultado = signal<ImportacaoResposta | null>(null);

  historico = signal<LoteHistorico[]>([]);
  aDesfazerId = signal<string | null>(null);

  ngOnInit() {
    this.carregarCatalogos();
    this.carregarHistorico();
  }

  private carregarCatalogos() {
    this.http.get<Curso[]>('/api/v1/academico/cursos').subscribe({ next: (v) => this.cursos.set(v) });
    this.http.get<SerieAno[]>('/api/v1/academico/series').subscribe({ next: (v) => this.series.set(v) });
    this.http.get<Turma[]>('/api/v1/academico/turmas').subscribe({ next: (v) => this.turmas.set(v) });
    this.http.get<Disciplina[]>('/api/v1/academico/disciplinas').subscribe({ next: (v) => this.disciplinas.set(v) });
  }

  private carregarHistorico() {
    this.http.get<LoteHistorico[]>('/api/v1/importacao/lotes').subscribe({ next: (v) => this.historico.set(v) });
  }

  seriesDoCurso(cursoId: string): SerieAno[] {
    return this.series().filter((s) => s.curso_id === cursoId);
  }

  turmasDaSerie(serieAnoId: string): Turma[] {
    return this.turmas().filter((t) => t.serie_ano_id === serieAnoId);
  }

  // ==========================================
  // PASSO 1 — upload + pré-visualização
  // ==========================================
  onSelecionarFicheiro(evento: Event) {
    const ficheiro = (evento.target as HTMLInputElement).files?.[0] ?? null;
    this.ficheiroSelecionado.set(ficheiro);
  }

  enviarParaPreview() {
    const ficheiro = this.ficheiroSelecionado();
    if (!ficheiro) return;

    this.erro.set(null);
    this.aProcessar.set(true);
    const dados = new FormData();
    dados.append('ficheiro', ficheiro);

    this.http.post<PreviewResposta>('/api/v1/importacao/mini-pauta/preview', dados).subscribe({
      next: (resp) => {
        this.aProcessar.set(false);
        this.preview.set(resp);

        const meta = resp.metadados;
        this.cursoEdicao.set(novaEntidadeEdicao());
        this.serieEdicao.set(novaEntidadeEdicao());
        this.turmaEdicao.set(novaEntidadeEdicao(meta.turma_nome_codigo ?? ''));
        this.disciplinaEdicao.set(novaEntidadeEdicao(meta.disciplina_nome ?? ''));
        this.anoLetivoEditado.set(meta.ano_letivo);
        this.trimestresEditados.set(resp.trimestres.map((t) => ({ ...t })));

        this.passoAtual.set(2);
      },
      error: (err) => {
        this.aProcessar.set(false);
        this.erro.set(this.extrairErro(err, 'Não foi possível processar o ficheiro. Confirme que é uma mini-pauta .xlsx válida.'));
      },
    });
  }

  // ==========================================
  // PASSO 2 — confirmação de metadados/entidades/pesos
  // ==========================================
  private entidadePreenchida(e: EntidadeEdicao): boolean {
    return e.modo === 'existente' ? !!e.id : e.nomeNovo.trim().length > 0;
  }

  podeAvancarParaAlunos(): boolean {
    return (
      !!this.anoLetivoEditado() &&
      this.entidadePreenchida(this.cursoEdicao()) &&
      this.entidadePreenchida(this.serieEdicao()) &&
      this.entidadePreenchida(this.turmaEdicao()) &&
      this.entidadePreenchida(this.disciplinaEdicao())
    );
  }

  atualizarPeso(index: number, campo: 'peso_mact' | 'peso_pt', valor: string) {
    const numero = Number(valor);
    this.trimestresEditados.update((lista) =>
      lista.map((t, i) => (i === index ? { ...t, [campo]: Number.isFinite(numero) ? numero : t[campo] } : t))
    );
  }

  avancarParaAlunos() {
    if (!this.podeAvancarParaAlunos()) return;
    const previewAtual = this.preview();
    if (!previewAtual) return;

    this.alunosEditados.set(
      previewAtual.alunos.map((a) => ({
        nome_completo: a.nome_completo,
        acao: a.aluno_existente_id ? 'REUTILIZAR_ALUNO_EXISTENTE' : 'CRIAR_NOVO_ALUNO',
        aluno_existente_id: a.aluno_existente_id,
        notas: a.notas,
      }))
    );
    this.passoAtual.set(3);
  }

  // ==========================================
  // PASSO 3 — plantel (ação por aluno) + confirmação final
  // ==========================================
  alternarAcaoAluno(index: number) {
    this.alunosEditados.update((lista) =>
      lista.map((a, i) => {
        if (i !== index) return a;
        // Só alterna para REUTILIZAR quando há mesmo uma correspondência
        // conhecida (aluno_existente_id) — sem isso não há para quem reutilizar.
        if (a.acao === 'CRIAR_NOVO_ALUNO' && a.aluno_existente_id) {
          return { ...a, acao: 'REUTILIZAR_ALUNO_EXISTENTE' as AcaoAluno };
        }
        return { ...a, acao: 'CRIAR_NOVO_ALUNO' as AcaoAluno };
      })
    );
  }

  private refPayload(e: EntidadeEdicao): { id?: string; nome_novo?: string } {
    return e.modo === 'existente' ? { id: e.id } : { nome_novo: e.nomeNovo.trim() };
  }

  confirmarImportacao() {
    const previewAtual = this.preview();
    const anoLetivo = this.anoLetivoEditado();
    if (!previewAtual || !anoLetivo) return;

    this.erro.set(null);
    this.aProcessar.set(true);

    const corpo = {
      curso: this.refPayload(this.cursoEdicao()),
      serie_ano: this.refPayload(this.serieEdicao()),
      turma: this.refPayload(this.turmaEdicao()),
      disciplina: this.refPayload(this.disciplinaEdicao()),
      ano_letivo: anoLetivo,
      trimestres: this.trimestresEditados().map((t) => ({
        nome: t.nome, tem_dados: t.tem_dados, peso_mact: t.peso_mact, peso_pt: t.peso_pt,
      })),
      alunos: this.alunosEditados(),
      nome_ficheiro_original: this.ficheiroSelecionado()?.name ?? 'mini-pauta.xlsx',
      chave_storage_ficheiro: previewAtual.metadados.chave_storage_ficheiro,
    };

    this.http.post<ImportacaoResposta>('/api/v1/importacao/mini-pauta/confirmar', corpo).subscribe({
      next: (resp) => {
        this.aProcessar.set(false);
        this.resultado.set(resp);
        this.passoAtual.set(4);
        this.carregarHistorico();
      },
      error: (err) => {
        this.aProcessar.set(false);
        this.erro.set(this.extrairErro(err, 'Não foi possível concluir a importação.'));
      },
    });
  }

  // ==========================================
  // Histórico / desfazer
  // ==========================================
  desfazer(loteId: string) {
    this.erro.set(null);
    this.aDesfazerId.set(loteId);
    this.http.post(`/api/v1/importacao/lotes/${loteId}/desfazer`, {}).subscribe({
      next: () => { this.aDesfazerId.set(null); this.carregarHistorico(); },
      error: (err) => {
        this.aDesfazerId.set(null);
        this.erro.set(this.extrairErro(err, 'Não foi possível desfazer esta importação.'));
      },
    });
  }

  novaImportacao() {
    this.passoAtual.set(1);
    this.ficheiroSelecionado.set(null);
    this.preview.set(null);
    this.resultado.set(null);
    this.erro.set(null);
    this.carregarCatalogos();
  }

  private extrairErro(err: unknown, mensagemOmissao: string): string {
    const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
    return typeof detail === 'string' ? detail : mensagemOmissao;
  }
}
