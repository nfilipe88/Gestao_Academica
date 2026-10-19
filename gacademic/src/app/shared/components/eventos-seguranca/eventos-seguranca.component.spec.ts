import { describe, expect, it, beforeEach } from 'vitest';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { EventosSegurancaComponent } from './eventos-seguranca.component';

describe('EventosSegurancaComponent', () => {
  let fixture: ComponentFixture<EventosSegurancaComponent>;
  let http: HttpTestingController;
  const raiz = () => fixture.nativeElement as HTMLElement;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    fixture = TestBed.createComponent(EventosSegurancaComponent);
    http = TestBed.inject(HttpTestingController);
  });

  it('carrega do url indicado com os filtros e mostra quem, de onde e o quê', () => {
    fixture.componentRef.setInput('url', '/api/v1/admin/seguranca/eventos');
    fixture.componentRef.setInput('mostrarEscola', true);
    fixture.componentRef.setInput('filtros', { ip: '203.0.113.7', tenant_id: '' });
    fixture.detectChanges();

    const pedido = http.expectOne(r => r.url === '/api/v1/admin/seguranca/eventos');
    expect(pedido.request.params.get('ip')).toBe('203.0.113.7');
    expect(pedido.request.params.has('tenant_id')).toBe(false);
    pedido.flush({
      items: [{
        id: '1', data_evento: '2026-10-19T10:00:00Z', tipo: 'TOKEN_FORJADO', gravidade: 'ALTA', ip: '203.0.113.7',
        user_agent: 'curl/8', email: null, metodo: 'GET', caminho: '/api/v1/perfil', detalhe: 'Assinatura inválida',
        tenant_id: null, nome_escola: null,
      }],
      total: 1, page: 1, page_size: 25, total_pages: 1,
    });
    fixture.detectChanges();

    const texto = raiz().textContent ?? '';
    expect(texto).toContain('Sessão forjada');
    expect(texto).toContain('Sem sessão');
    expect(texto).toContain('203.0.113.7');
    expect(texto).toContain('Alta');
  });

  it('filtrar por gravidade volta a pedir à 1.ª página', () => {
    fixture.componentRef.setInput('url', '/api/v1/seguranca/eventos');
    fixture.detectChanges();
    http.expectOne(r => r.url === '/api/v1/seguranca/eventos').flush({ items: [], total: 0, page: 1, page_size: 25, total_pages: 0 });

    fixture.componentInstance.onGravidade('ALTA');
    const pedido = http.expectOne(r => r.url === '/api/v1/seguranca/eventos');
    expect(pedido.request.params.get('gravidade')).toBe('ALTA');
    expect(pedido.request.params.get('page')).toBe('1');
    pedido.flush({ items: [], total: 0, page: 1, page_size: 25, total_pages: 0 });
    fixture.detectChanges();
    expect(raiz().textContent).toContain('Nenhuma tentativa de acesso indevido registada.');
  });
});
