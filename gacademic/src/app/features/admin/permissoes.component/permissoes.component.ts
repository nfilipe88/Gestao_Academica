import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, computed, effect, inject, OnInit, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Store } from '@ngrx/store';
import { map } from 'rxjs';
import { carregarPermissoes, atualizarPermissao } from '../../../store/permissoes/permissoes.actions';
import { selectPermissoes, selectPermissoesError } from '../../../store/permissoes/permissoes.selector';
import { OperacoesCrud, PerfilPermissao, PermissaoModulo } from '../../../store/permissoes/permissoes.models';
import { PopoverComponent } from '../../../shared/components/popover/popover.component/popover.component';
import { NomePerfilPipe } from '../../../shared/pipes/nome-perfil.pipe';
import { NomesPerfisService } from '../../../core/services/nomes-perfis.service';
import { selectIsGestor, selectIsSuperAdmin } from '../../../store/auth/auth.selectors';
import { PerfilBaseEscola, PerfilEscola, PerfisEscolaService, PermissaoPerfilEscola } from '../../../core/services/perfis-escola.service';
import { AvisoLeitura, avisosDeLeitura } from './avisos-leitura';

// Perfis fixos da plataforma (ver app/core/security.py::exigir_perfil no
// back-end). Os perfis de cada escola (ex.: "Tesouraria") aparecem como
// colunas a seguir a estes, só na vista do Gestor — ver PerfisEscolaService.
const PERFIS: { id: PerfilPermissao; label: string }[] = [
  { id: 'super_admin', label: 'Super Admin' },
  { id: 'gestor', label: 'Gestor' },
  { id: 'secretaria', label: 'Secretaria' },
  { id: 'professor', label: 'Professor' },
  { id: 'aluno_responsavel', label: 'Aluno / Resp.' },
];

// As 4 operações que o dropdown de cada célula oferece — a ordem aqui é
// a ordem em que aparecem no popover.
const OPERACOES: { chave: keyof OperacoesCrud; letra: string; label: string }[] = [
  { chave: 'pode_criar', letra: 'C', label: 'Criar' },
  { chave: 'pode_ler', letra: 'R', label: 'Ler' },
  { chave: 'pode_atualizar', letra: 'U', label: 'Atualizar' },
  { chave: 'pode_apagar', letra: 'D', label: 'Apagar' },
];

interface LinhaModulo {
  ordem: number;
  modulo: string;
  porPerfil: Partial<Record<PerfilPermissao, PermissaoModulo>>;
}

@Component({
  selector: 'app-permissoes.component',
  imports: [CommonModule, AsyncPipe, FormsModule, PopoverComponent, NomePerfilPipe],
  templateUrl: './permissoes.component.html',
  styleUrl: './permissoes.component.css',
})
export class PermissoesComponent implements OnInit {
  private store = inject(Store);

  perfis = PERFIS;
  operacoes = OPERACOES;

  erro$ = this.store.select(selectPermissoesError);
  isSuperAdmin$ = this.store.select(selectIsSuperAdmin);
  nomesPerfis = inject(NomesPerfisService);
  mensagemNomes = signal<string | null>(null);
  erroNomes = signal(false);

  // Cabeçalho de cada coluna com os nomes definidos pelo Super Admin.
  rotuloColuna(id: PerfilPermissao): string {
    const codigos: Record<string, string[]> = {
      super_admin: ['SUPER_ADMIN'], gestor: ['GESTOR'], secretaria: ['SECRETARIA'],
      professor: ['PROFESSOR'], aluno_responsavel: ['ALUNO', 'RESPONSAVEL'],
    };
    return (codigos[id] ?? [id]).map(c => this.nomesPerfis.nome(c)).join(' / ');
  }

  onRenomear(codigo: string, nome: string) {
    this.mensagemNomes.set(null);
    this.nomesPerfis.renomear(codigo, nome).subscribe({
      next: (p) => { this.erroNomes.set(false); this.mensagemNomes.set(`Nome guardado: ${p.codigo} → "${p.nome}".`); },
      error: (err) => { this.erroNomes.set(true); this.mensagemNomes.set(err.error?.detail || 'Não foi possível guardar o nome.'); },
    });
  }

  // Agrupa a lista plana (uma linha por módulo x perfil, ver
  // schemas/permissoes.py) em linhas por módulo — mantém a mesma forma
  // de tabela (módulo nas linhas, perfil nas colunas) que o mapa
  // sempre teve, só que agora construída a partir dos dados carregados
  // do back-end em vez de um array hardcoded.
  linhas$ = this.store.select(selectPermissoes).pipe(
    map(lista => {
      const porModulo = new Map<string, LinhaModulo>();
      for (const p of lista) {
        if (!porModulo.has(p.modulo)) {
          porModulo.set(p.modulo, { ordem: p.ordem, modulo: p.modulo, porPerfil: {} });
        }
        porModulo.get(p.modulo)!.porPerfil[p.perfil] = p;
      }
      return Array.from(porModulo.values()).sort((a, b) => a.ordem - b.ordem);
    })
  );

  ngOnInit() {
    this.store.dispatch(carregarPermissoes());
  }

  // ==========================================
  // Perfis da escola (só o Gestor): colunas extra na matriz
  // ==========================================
  perfisEscola = inject(PerfisEscolaService);
  eGestor = toSignal(this.store.select(selectIsGestor), { initialValue: false });
  mensagemPerfisEscola = signal<string | null>(null);
  erroPerfisEscola = signal(false);
  perfilAApagarId = signal<string | null>(null);

  // Só o Gestor tem perfis da escola — o Super Admin nem pergunta (um 403
  // ficava nos Eventos de Segurança).
  private carregarPerfisEscola = effect(() => {
    if (this.eGestor()) this.perfisEscola.carregar();
  });

  private avisarPerfis(texto: string, erro = false) {
    this.erroPerfisEscola.set(erro);
    this.mensagemPerfisEscola.set(texto);
  }

  onCriarPerfilEscola(nome: string, base: string, campo: HTMLInputElement) {
    this.mensagemPerfisEscola.set(null);
    this.perfisEscola.criar(nome, base as PerfilBaseEscola).subscribe({
      next: (p) => {
        campo.value = '';
        this.avisarPerfis(`Perfil "${p.nome}" criado, igual a ${this.nomesPerfis.nome(p.perfil_base)} na escola. Desmarque na coluna dele o que não deve poder fazer e atribua-o em Gestão de Acessos.`);
      },
      error: (err) => this.avisarPerfis(err.error?.detail || 'Não foi possível criar o perfil.', true),
    });
  }

  onRenomearPerfilEscola(perfil: PerfilEscola, nome: string) {
    this.mensagemPerfisEscola.set(null);
    this.perfisEscola.renomear(perfil.id, nome).subscribe({
      next: (p) => this.avisarPerfis(`Nome guardado: "${p.nome}".`),
      error: (err) => this.avisarPerfis(err.error?.detail || 'Não foi possível guardar o nome.', true),
    });
  }

  onApagarPerfilEscola(perfil: PerfilEscola) {
    this.perfilAApagarId.set(null);
    this.perfisEscola.apagar(perfil.id).subscribe({
      next: () => this.avisarPerfis(`Perfil "${perfil.nome}" apagado — quem o tinha voltou a ${this.nomesPerfis.nome(perfil.perfil_base)}.`),
      error: (err) => this.avisarPerfis(err.error?.detail || 'Não foi possível apagar o perfil.', true),
    });
  }

  celulaEscola(perfil: PerfilEscola, modulo: string): PermissaoPerfilEscola | undefined {
    return perfil.permissoes.find(p => p.modulo === modulo);
  }

  bloqueioEscola(perfil: PerfilEscola, celula: PermissaoPerfilEscola, op: keyof OperacoesCrud): string | null {
    if (celula.informativo) return 'Linha só informativa — não há páginas associadas a restringir.';
    if (celula.protegidas?.includes(op)) return 'Protegida: toda a aplicação precisa disto (moeda, ano letivo).';
    if (!celula[`limite_${op}` as keyof PermissaoPerfilEscola]) return `${this.nomesPerfis.nome(perfil.perfil_base)} não pode isto na escola — um perfil da escola só pode ter menos.`;
    return null;
  }

  avisosPerfil(perfil: PerfilEscola): (AvisoLeitura & { corrigivel: boolean })[] {
    const celulas = perfil.permissoes.map(p => ({
      ...p, ler: p.pode_ler, escreve: p.pode_criar || p.pode_atualizar || p.pode_apagar,
    }));
    return avisosDeLeitura(celulas).map(aviso => ({
      ...aviso, corrigivel: !!this.celulaEscola(perfil, aviso.precisa)?.limite_pode_ler,
    }));
  }

  onDarLeituraPerfil(perfil: PerfilEscola, modulo: string) {
    const celula = this.celulaEscola(perfil, modulo);
    if (!celula) return;
    this.mensagemPerfisEscola.set(null);
    this.perfisEscola.atualizarModulo(perfil.id, modulo, {
      pode_criar: celula.pode_criar, pode_ler: true,
      pode_atualizar: celula.pode_atualizar, pode_apagar: celula.pode_apagar,
    }).subscribe({
      error: (err) => this.avisarPerfis(err.error?.detail || 'Não foi possível guardar esta permissão.', true),
    });
  }

  // O mesmo aviso para as restrições do próprio mapa (ex.: tirar à Secretaria ler Alunos).
  private permissoes = toSignal(this.store.select(selectPermissoes), { initialValue: [] as PermissaoModulo[] });
  avisosMapa = computed(() => {
    const avisos: (AvisoLeitura & { perfil: PerfilPermissao; corrigivel: boolean })[] = [];
    for (const perfil of ['gestor', 'secretaria', 'professor'] as PerfilPermissao[]) {
      const celulas = this.permissoes().filter(p => p.perfil === perfil);
      const paraAviso = celulas.map(c => ({
        ...c, ler: this.valor(c, 'pode_ler'),
        escreve: this.valor(c, 'pode_criar') || this.valor(c, 'pode_atualizar') || this.valor(c, 'pode_apagar'),
      }));
      for (const aviso of avisosDeLeitura(paraAviso)) {
        const necessaria = celulas.find(c => c.modulo === aviso.precisa);
        if (necessaria) avisos.push({ ...aviso, perfil, corrigivel: !this.bloqueio(necessaria, 'pode_ler') });
      }
    }
    return avisos;
  });

  onDarLeituraMapa(perfil: PerfilPermissao, modulo: string) {
    const celula = this.permissoes().find(p => p.perfil === perfil && p.modulo === modulo);
    if (!celula) return;
    const operacoes: OperacoesCrud = {
      pode_criar: this.valor(celula, 'pode_criar'), pode_ler: true,
      pode_atualizar: this.valor(celula, 'pode_atualizar'), pode_apagar: this.valor(celula, 'pode_apagar'),
    };
    this.store.dispatch(atualizarPermissao({ id: celula.id, operacoes, escola: !this.eSuperAdminSinal() }));
  }

  resumoEscola(celula: PermissaoPerfilEscola | undefined): string {
    if (!celula) return '—';
    const letras = OPERACOES.filter(op => celula[op.chave]).map(op => op.letra);
    return letras.length ? letras.join('') : '—';
  }

  classeEscola(celula: PermissaoPerfilEscola | undefined): string {
    const n = celula ? OPERACOES.filter(op => celula[op.chave]).length : 0;
    if (n === 0) return 'bg-slate-100 text-slate-400';
    if (n === OPERACOES.length) return 'bg-emerald-100 text-emerald-700';
    return 'bg-amber-100 text-amber-700';
  }

  onAlterarEscola(perfil: PerfilEscola, celula: PermissaoPerfilEscola, chave: keyof OperacoesCrud, event: Event) {
    const marcado = (event.target as HTMLInputElement).checked;
    const operacoes: OperacoesCrud = {
      pode_criar: celula.pode_criar, pode_ler: celula.pode_ler,
      pode_atualizar: celula.pode_atualizar, pode_apagar: celula.pode_apagar,
      [chave]: marcado,
    };
    this.mensagemPerfisEscola.set(null);
    this.perfisEscola.atualizarModulo(perfil.id, celula.modulo, operacoes).subscribe({
      error: (err) => {
        (event.target as HTMLInputElement).checked = !marcado;
        this.avisarPerfis(err.error?.detail || 'Não foi possível guardar esta permissão.', true);
      },
    });
  }

  // Super Admin edita o mapa base (todas as escolas); o Gestor vê e restringe
  // o que vale na escola dele — ver back_end/app/core/mapa_permissoes.py.
  eSuperAdminSinal = toSignal(this.store.select(selectIsSuperAdmin), { initialValue: false });

  valor(celula: PermissaoModulo, op: keyof OperacoesCrud): boolean {
    if (this.eSuperAdminSinal()) return celula[op];
    const daEscola = celula[`escola_${op}` as keyof PermissaoModulo];
    return typeof daEscola === 'boolean' ? daEscola : celula[op];
  }

  // Porque é que uma operação não se pode mudar (null = pode).
  bloqueio(celula: PermissaoModulo, op: keyof OperacoesCrud): string | null {
    if (celula.perfil === 'super_admin') return 'A equipa da plataforma não é restringida pelo mapa.';
    if (celula.protegidas?.includes(op) && this.valor(celula, op)) return 'Protegida: a plataforma precisa disto para funcionar.';
    if (this.eSuperAdminSinal()) {
      if (!celula[`codigo_${op}` as keyof PermissaoModulo] && !celula[op]) return 'O código não permite isto a este perfil — o mapa só restringe.';
      return null;
    }
    if (celula.informativo) return 'Linha só informativa — não há páginas associadas a restringir.';
    if (!celula[op]) return 'O mapa base da plataforma não dá isto a este perfil — a escola só pode restringir.';
    return null;
  }

  // Quantas operações estão ativas nesta célula — usado só para pintar
  // o resumo visual (verde/âmbar/cinzento) no gatilho do dropdown; o
  // popover é que manda no que está realmente marcado.
  contarOperacoes(celula: PermissaoModulo | undefined): number {
    if (!celula) return 0;
    return OPERACOES.filter(op => this.valor(celula, op.chave)).length;
  }

  classeResumo(celula: PermissaoModulo | undefined): string {
    const n = this.contarOperacoes(celula);
    if (n === 0) return 'bg-slate-100 text-slate-400';
    if (n === OPERACOES.length) return 'bg-emerald-100 text-emerald-700';
    return 'bg-amber-100 text-amber-700';
  }

  resumoTexto(celula: PermissaoModulo | undefined): string {
    if (!celula) return '—';
    const letras = OPERACOES.filter(op => this.valor(celula, op.chave)).map(op => op.letra);
    return letras.length ? letras.join('') : '—';
  }

  // Disparado por cada checkbox do popover — sem botão "Guardar" à
  // parte, cada alteração já atualiza a célula de imediato. O popover
  // fica aberto (só fecha ao clicar fora ou Escape) para permitir
  // marcar várias operações seguidas sem reabrir.
  onAlterarOperacao(celula: PermissaoModulo, chave: keyof OperacoesCrud, event: Event) {
    const marcado = (event.target as HTMLInputElement).checked;
    const operacoes: OperacoesCrud = {
      pode_criar: this.valor(celula, 'pode_criar'),
      pode_ler: this.valor(celula, 'pode_ler'),
      pode_atualizar: this.valor(celula, 'pode_atualizar'),
      pode_apagar: this.valor(celula, 'pode_apagar'),
      [chave]: marcado,
    };
    this.store.dispatch(atualizarPermissao({ id: celula.id, operacoes, escola: !this.eSuperAdminSinal() }));
  }
}
