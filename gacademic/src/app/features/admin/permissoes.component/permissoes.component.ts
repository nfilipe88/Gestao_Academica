import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { Store } from '@ngrx/store';
import { map } from 'rxjs';
import { carregarPermissoes, atualizarPermissao } from '../../../store/permissoes/permissoes.actions';
import { selectPermissoes, selectPermissoesError } from '../../../store/permissoes/permissoes.selector';
import { OperacoesCrud, PerfilPermissao, PermissaoModulo } from '../../../store/permissoes/permissoes.models';

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

// As 4 operações que a combobox de cada célula oferece — a ordem aqui é
// a ordem em que aparecem no <select multiple>.
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
  imports: [CommonModule, AsyncPipe],
  templateUrl: './permissoes.component.html',
  styleUrl: './permissoes.component.css',
})
export class PermissoesComponent implements OnInit {
  private store = inject(Store);

  perfis = PERFIS;
  operacoes = OPERACOES;

  erro$ = this.store.select(selectPermissoesError);

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

  // Quantas operações estão ativas nesta célula — usado só para pintar
  // o resumo visual (verde/âmbar/cinzento), o combobox é que manda.
  contarOperacoes(celula: PermissaoModulo | undefined): number {
    if (!celula) return 0;
    return OPERACOES.filter(op => celula[op.chave]).length;
  }

  classeResumo(celula: PermissaoModulo | undefined): string {
    const n = this.contarOperacoes(celula);
    if (n === 0) return 'bg-slate-100 text-slate-400';
    if (n === OPERACOES.length) return 'bg-emerald-100 text-emerald-700';
    return 'bg-amber-100 text-amber-700';
  }

  resumoTexto(celula: PermissaoModulo | undefined): string {
    if (!celula) return '—';
    const letras = OPERACOES.filter(op => celula[op.chave]).map(op => op.letra);
    return letras.length ? letras.join('') : '—';
  }

  // Disparado pelo (change) do <select multiple> — sem botão "Guardar"
  // à parte, a seleção já atualiza a célula de imediato.
  onAlterarOperacoes(celula: PermissaoModulo, event: Event) {
    const selecionadas = new Set(
      Array.from((event.target as HTMLSelectElement).selectedOptions).map(o => o.value)
    );
    const operacoes: OperacoesCrud = {
      pode_criar: selecionadas.has('pode_criar'),
      pode_ler: selecionadas.has('pode_ler'),
      pode_atualizar: selecionadas.has('pode_atualizar'),
      pode_apagar: selecionadas.has('pode_apagar'),
    };
    this.store.dispatch(atualizarPermissao({ id: celula.id, operacoes }));
  }
}
