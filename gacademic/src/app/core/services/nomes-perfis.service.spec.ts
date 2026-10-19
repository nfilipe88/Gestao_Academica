import { describe, expect, it, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { NomesPerfisService } from './nomes-perfis.service';
import { NomePerfilPipe } from '../../shared/pipes/nome-perfil.pipe';

describe('NomesPerfisService / nomePerfil', () => {
  let servico: NomesPerfisService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    servico = TestBed.inject(NomesPerfisService);
    http = TestBed.inject(HttpTestingController);
  });

  it('antes de carregar mostra um nome legível, nunca o código cru', () => {
    expect(servico.nome('GESTOR')).toBe('Gestor');
    expect(servico.nome('RESPONSAVEL')).toBe('Responsável');
    expect(servico.nome(null)).toBe('');
  });

  it('depois de carregar usa os nomes definidos pelo Super Admin, também no pipe', () => {
    servico.carregar();
    http.expectOne('/api/v1/permissoes/perfis').flush([
      { codigo: 'GESTOR', nome: 'Diretor Geral' }, { codigo: 'SECRETARIA', nome: 'Secretaria' },
    ]);
    expect(servico.nome('GESTOR')).toBe('Diretor Geral');
    const pipe = TestBed.runInInjectionContext(() => new NomePerfilPipe());
    expect(pipe.transform('GESTOR')).toBe('Diretor Geral');
  });

  it('renomear atualiza logo o nome em toda a app', () => {
    servico.carregar();
    http.expectOne('/api/v1/permissoes/perfis').flush([{ codigo: 'GESTOR', nome: 'Gestor' }]);
    servico.renomear('GESTOR', 'Diretor').subscribe();
    const pedido = http.expectOne('/api/v1/permissoes/perfis/GESTOR');
    expect(pedido.request.method).toBe('PUT');
    expect(pedido.request.body).toEqual({ nome: 'Diretor' });
    pedido.flush({ codigo: 'GESTOR', nome: 'Diretor' });
    expect(servico.nome('GESTOR')).toBe('Diretor');
  });
});
