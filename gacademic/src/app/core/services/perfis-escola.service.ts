import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { OperacoesCrud } from '../../store/permissoes/permissoes.models';

export type PerfilBaseEscola = 'SECRETARIA' | 'PROFESSOR';

export interface PermissaoPerfilEscola extends OperacoesCrud {
  modulo: string;
  ordem: number;
  informativo: boolean;
  // O que o perfil base pode na escola — o teto deste perfil.
  limite_pode_criar: boolean;
  limite_pode_ler: boolean;
  limite_pode_atualizar: boolean;
  limite_pode_apagar: boolean;
}

export interface PerfilEscola {
  id: string;
  nome: string;
  perfil_base: PerfilBaseEscola;
  n_utilizadores: number;
  permissoes: PermissaoPerfilEscola[];
}

/**
 * Perfis da escola (ex.: "Tesouraria"), criados pelo Gestor a partir da
 * Secretaria ou do Professor, só com menos permissões — ver
 * back_end/app/cruds/perfis_personalizados.py. Usado no Mapa de Permissões
 * (editar) e na Gestão de Acessos (atribuir).
 */
@Injectable({ providedIn: 'root' })
export class PerfisEscolaService {
  private http = inject(HttpClient);
  private readonly url = '/api/v1/perfis-personalizados';

  readonly perfis = signal<PerfilEscola[]>([]);

  carregar(): void {
    this.http.get<PerfilEscola[]>(this.url).subscribe({
      next: (lista) => this.perfis.set(lista),
      error: () => this.perfis.set([]),
    });
  }

  criar(nome: string, perfil_base: PerfilBaseEscola): Observable<PerfilEscola> {
    return this.http.post<PerfilEscola>(this.url, { nome, perfil_base }).pipe(
      tap(novo => this.perfis.update(lista => [...lista, novo].sort((a, b) => a.nome.localeCompare(b.nome)))),
    );
  }

  renomear(id: string, nome: string): Observable<PerfilEscola> {
    return this.http.patch<PerfilEscola>(`${this.url}/${id}`, { nome }).pipe(tap(p => this.substituir(p)));
  }

  atualizarModulo(id: string, modulo: string, operacoes: OperacoesCrud): Observable<PerfilEscola> {
    return this.http.put<PerfilEscola>(`${this.url}/${id}/permissoes`, { modulo, ...operacoes }).pipe(tap(p => this.substituir(p)));
  }

  apagar(id: string): Observable<void> {
    return this.http.delete<void>(`${this.url}/${id}`).pipe(
      tap(() => this.perfis.update(lista => lista.filter(p => p.id !== id))),
    );
  }

  private substituir(perfil: PerfilEscola): void {
    this.perfis.update(lista => lista.map(p => (p.id === perfil.id ? perfil : p)));
  }
}
