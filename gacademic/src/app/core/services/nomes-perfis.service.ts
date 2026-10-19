import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

export interface PerfilNome {
  codigo: string;
  nome: string;
}

/**
 * Nomes mostrados dos perfis (ex.: GESTOR → "Diretor Geral"), definidos
 * pelo Super Admin para toda a plataforma — ver
 * back_end/app/database/models_permissoes.py::PerfilNome. O código
 * (GESTOR, SECRETARIA, …) continua a ser o que decide as permissões; isto
 * é só o que se lê. Carregado pelo layout autenticado (DashboardLayout).
 */
@Injectable({ providedIn: 'root' })
export class NomesPerfisService {
  private http = inject(HttpClient);

  readonly perfis = signal<PerfilNome[]>([]);

  carregar(): void {
    this.http.get<PerfilNome[]>('/api/v1/permissoes/perfis').subscribe({
      next: (lista) => this.perfis.set(lista),
      error: () => { /* sem nomes personalizados, mostram-se os de omissão */ },
    });
  }

  /** Nome mostrado de um código; antes de carregar, um nome legível a partir do código. */
  nome(codigo: string | null | undefined): string {
    if (!codigo) return '';
    return this.perfis().find(p => p.codigo === codigo)?.nome ?? NOMES_OMISSAO[codigo] ?? codigo;
  }

  renomear(codigo: string, nome: string): Observable<PerfilNome> {
    return this.http.put<PerfilNome>(`/api/v1/permissoes/perfis/${codigo}`, { nome }).pipe(
      tap(atualizado => this.perfis.update(lista => lista.map(p => (p.codigo === codigo ? atualizado : p)))),
    );
  }
}

const NOMES_OMISSAO: Record<string, string> = {
  SUPER_ADMIN: 'Super Admin',
  GESTOR: 'Gestor',
  SECRETARIA: 'Secretaria',
  PROFESSOR: 'Professor',
  ALUNO: 'Aluno',
  RESPONSAVEL: 'Responsável',
};
