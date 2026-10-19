import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit, signal } from '@angular/core';
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
import { selectIsSuperAdmin } from '../../../store/auth/auth.selectors';

// Perfis fixos da plataforma (ver app/core/security.py::exigir_perfil no
// back-end). Não confundir com "Perfis Personalizados" — uma
// funcionalidade futura, ainda não implementada, que permitirá a cada
// escola criar os seus próprios perfis com atributos configuráveis.
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
    if (celula.protegidas?.includes(op) && this.valor(celula, op)) return 'Protegida: o Gestor nunca perde esta permissão.';
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
