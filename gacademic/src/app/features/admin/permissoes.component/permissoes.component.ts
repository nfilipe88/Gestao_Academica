import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

// Perfis fixos da plataforma (ver app/core/security.py::exigir_perfil no
// back-end). Não confundir com "Perfis Personalizados" — uma
// funcionalidade futura, ainda não implementada, que permitirá a cada
// escola criar os seus próprios perfis com atributos configuráveis.
type Perfil = 'super_admin' | 'gestor' | 'secretaria' | 'professor' | 'aluno_responsavel';

type NivelAcesso = 'TOTAL' | 'PARCIAL' | 'LEITURA' | 'NENHUM';

interface LinhaModulo {
  modulo: string;
  acessos: Record<Perfil, NivelAcesso>;
}

const PERFIS: { id: Perfil; label: string }[] = [
  { id: 'super_admin', label: 'Super Admin' },
  { id: 'gestor', label: 'Gestor' },
  { id: 'secretaria', label: 'Secretaria' },
  { id: 'professor', label: 'Professor' },
  { id: 'aluno_responsavel', label: 'Aluno / Resp.' },
];

// Matriz construída a partir de cada exigir_perfil(...) do back-end
// (app/api/v1/*.py) e confirmada com login real em cada perfil. Manter
// isto atualizado sempre que um endpoint mudar de perfil exigido.
const MODULOS: LinhaModulo[] = [
  { modulo: 'Visão Geral', acessos: { super_admin: 'NENHUM', gestor: 'LEITURA', secretaria: 'LEITURA', professor: 'LEITURA', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Cursos', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'TOTAL', professor: 'LEITURA', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Turmas & Matrículas', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'TOTAL', professor: 'LEITURA', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Alunos & Responsáveis', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'TOTAL', professor: 'LEITURA', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Diário de Classe', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'TOTAL', professor: 'PARCIAL', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Trabalhos / Tarefas', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'TOTAL', professor: 'PARCIAL', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Horários', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'TOTAL', professor: 'LEITURA', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Comunicações', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'TOTAL', professor: 'PARCIAL', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Documentos (interno)', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'PARCIAL', professor: 'PARCIAL', aluno_responsavel: 'NENHUM' } },
  { modulo: 'CRM', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'TOTAL', professor: 'NENHUM', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Financeiro', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'TOTAL', professor: 'NENHUM', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Transferências de Alunos', acessos: { super_admin: 'PARCIAL', gestor: 'PARCIAL', secretaria: 'PARCIAL', professor: 'NENHUM', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Professores', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'PARCIAL', professor: 'LEITURA', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Indicadores', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'TOTAL', professor: 'NENHUM', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Configurações', acessos: { super_admin: 'NENHUM', gestor: 'TOTAL', secretaria: 'NENHUM', professor: 'NENHUM', aluno_responsavel: 'NENHUM' } },
  { modulo: 'Portal (próprio / educandos)', acessos: { super_admin: 'NENHUM', gestor: 'NENHUM', secretaria: 'NENHUM', professor: 'NENHUM', aluno_responsavel: 'TOTAL' } },
  { modulo: 'Instituições (multi-escola)', acessos: { super_admin: 'TOTAL', gestor: 'NENHUM', secretaria: 'NENHUM', professor: 'NENHUM', aluno_responsavel: 'NENHUM' } },
];

const CLASSES_NIVEL: Record<NivelAcesso, string> = {
  TOTAL: 'bg-emerald-100 text-emerald-700',
  PARCIAL: 'bg-amber-100 text-amber-700',
  LEITURA: 'bg-slate-100 text-slate-600',
  NENHUM: '',
};

const LABELS_NIVEL: Record<NivelAcesso, string> = {
  TOTAL: 'Total',
  PARCIAL: 'Parcial',
  LEITURA: 'Leitura',
  NENHUM: '—',
};

@Component({
  selector: 'app-permissoes.component',
  imports: [CommonModule],
  templateUrl: './permissoes.component.html',
  styleUrl: './permissoes.component.css',
})
export class PermissoesComponent {
  perfis = PERFIS;
  modulos = MODULOS;

  classeNivel(perfil: Perfil, modulo: LinhaModulo): string {
    return CLASSES_NIVEL[modulo.acessos[perfil]];
  }

  labelNivel(perfil: Perfil, modulo: LinhaModulo): string {
    return LABELS_NIVEL[modulo.acessos[perfil]];
  }
}
