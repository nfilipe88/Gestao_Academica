import { inject, Injectable } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { HttpClient } from '@angular/common/http';
import * as UsuariosActions from './usuarios.actions';
import { UsuarioAuditoriaRegisto, UsuarioStaff } from './usuarios.models';
import { PaginaResultado } from '../../shared/models/paginacao.models';
import { catchError, map, of, switchMap } from 'rxjs';

// Sem tenant_id -> escola do Gestor (token); com tenant_id -> qualquer
// escola, só o Super Admin tem acesso a essa rota no back-end.
function baseUrl(tenant_id?: string): string {
  return tenant_id ? `/api/v1/admin/tenants/${tenant_id}/usuarios` : '/api/v1/usuarios';
}

@Injectable()
export class UsuariosEffects {
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  carregarUsuarios$ = createEffect(() =>
    this.actions$.pipe(
      ofType(UsuariosActions.carregarUsuarios),
      switchMap(action => this.http.get<PaginaResultado<UsuarioStaff>>(baseUrl(action.tenant_id), {
        params: { page: action.page ?? 1, page_size: action.page_size ?? 25 }
      }).pipe(
        map(resp => UsuariosActions.carregarUsuariosSucesso({
          usuarios: resp.items,
          paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
        })),
        catchError(err => of(UsuariosActions.usuariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar os utilizadores.'
        })))
      ))
    )
  );

  criarSecretaria$ = createEffect(() =>
    this.actions$.pipe(
      ofType(UsuariosActions.criarSecretaria),
      switchMap(action => this.http.post<{ mensagem: string }>(`${baseUrl(action.tenant_id)}/secretaria`, {
        nome_completo: action.nome_completo, email: action.email, palavra_passe: action.palavra_passe
      }).pipe(
        switchMap(resp => [
          UsuariosActions.carregarUsuarios({ tenant_id: action.tenant_id }),
          UsuariosActions.usuariosOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(UsuariosActions.usuariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível criar a conta de Secretaria.'
        })))
      ))
    )
  );

  alterarPerfil$ = createEffect(() =>
    this.actions$.pipe(
      ofType(UsuariosActions.alterarPerfil),
      switchMap(action => this.http.patch<{ mensagem: string }>(
        `${baseUrl(action.tenant_id)}/${action.usuario_id}/perfil`, { perfil_acesso: action.perfil_acesso }
      ).pipe(
        switchMap(resp => [
          UsuariosActions.carregarUsuarios({ tenant_id: action.tenant_id }),
          UsuariosActions.usuariosOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(UsuariosActions.usuariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível mudar o perfil deste utilizador.'
        })))
      ))
    )
  );

  alterarAtivo$ = createEffect(() =>
    this.actions$.pipe(
      ofType(UsuariosActions.alterarAtivo),
      switchMap(action => this.http.patch<{ mensagem: string }>(
        `${baseUrl(action.tenant_id)}/${action.usuario_id}/ativo`, { ativo: action.ativo }
      ).pipe(
        switchMap(resp => [
          UsuariosActions.carregarUsuarios({ tenant_id: action.tenant_id }),
          UsuariosActions.usuariosOperacaoSucesso({ mensagem: resp.mensagem })
        ]),
        catchError(err => of(UsuariosActions.usuariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível alterar o estado deste utilizador.'
        })))
      ))
    )
  );

  carregarAuditoria$ = createEffect(() =>
    this.actions$.pipe(
      ofType(UsuariosActions.carregarAuditoria),
      switchMap(action => this.http.get<PaginaResultado<UsuarioAuditoriaRegisto>>(`${baseUrl(action.tenant_id)}/auditoria`, {
        params: { page: action.page ?? 1, page_size: action.page_size ?? 25 }
      }).pipe(
        map(resp => UsuariosActions.carregarAuditoriaSucesso({
          auditoria: resp.items,
          paginacao: { total: resp.total, page: resp.page, page_size: resp.page_size, total_pages: resp.total_pages }
        })),
        catchError(err => of(UsuariosActions.usuariosOperacaoFalhou({
          erro: err.error?.detail || 'Não foi possível carregar o histórico de acessos.'
        })))
      ))
    )
  );
}
