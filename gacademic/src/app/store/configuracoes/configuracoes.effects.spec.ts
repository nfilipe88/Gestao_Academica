import { beforeEach, describe, expect, it } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideMockActions } from '@ngrx/effects/testing';
import { Observable, of, Subject } from 'rxjs';
import { Action } from '@ngrx/store';
import { ConfiguracoesEffects } from './configuracoes.effects';
import * as Acoes from './configuracoes.actions';
import { CONFIGURACAO_INICIAL } from './configuracoes.models';
import { configuracoesReducer, initialState } from './configuracoes.reducer';

describe('ConfiguracoesEffects — inscrições e termos', () => {
  let acoes$: Subject<Action>;
  let efeitos: ConfiguracoesEffects;
  let backend: HttpTestingController;

  beforeEach(() => {
    acoes$ = new Subject<Action>();
    TestBed.configureTestingModule({
      providers: [ConfiguracoesEffects, provideHttpClient(), provideHttpClientTesting(), provideMockActions(() => acoes$ as Observable<Action>)],
    });
    efeitos = TestBed.inject(ConfiguracoesEffects);
    backend = TestBed.inject(HttpTestingController);
  });

  it('encerrar rematrículas faz PATCH só com o campo alterado e atualiza a configuração', () => {
    const emitidas: Action[] = [];
    efeitos.atualizarInscricoes$.subscribe(a => emitidas.push(a));

    acoes$.next(Acoes.atualizarInscricoes({ dados: { rematriculas_abertas: false } }));
    const pedido = backend.expectOne('/api/v1/configuracoes/inscricoes');
    expect(pedido.request.method).toBe('PATCH');
    expect(pedido.request.body).toEqual({ rematriculas_abertas: false });
    pedido.flush({ ...CONFIGURACAO_INICIAL, matriculas_abertas: true, rematriculas_abertas: false });

    expect(emitidas.map(a => a.type)).toEqual([Acoes.carregarConfiguracaoSucesso.type, Acoes.configuracoesOperacaoSucesso.type]);
    const estado = configuracoesReducer(initialState, emitidas[0]);
    expect(estado.configuracao.rematriculas_abertas).toBe(false);
    expect(estado.configuracao.matriculas_abertas).toBe(true);
  });

  it('se o servidor recusar, devolve o erro e não altera a configuração', () => {
    const emitidas: Action[] = [];
    efeitos.atualizarInscricoes$.subscribe(a => emitidas.push(a));
    acoes$.next(Acoes.atualizarInscricoes({ dados: { matriculas_abertas: false } }));
    backend.expectOne('/api/v1/configuracoes/inscricoes').flush({ detail: 'Sem permissão.' }, { status: 403, statusText: 'Forbidden' });
    expect(emitidas).toHaveLength(1);
    expect((emitidas[0] as any).erro).toBe('Sem permissão.');
  });

  it('aceitar os termos faz POST e guarda a data de aceitação', () => {
    const emitidas: Action[] = [];
    efeitos.aceitarTermos$.subscribe(a => emitidas.push(a));
    acoes$.next(Acoes.aceitarTermos());
    const pedido = backend.expectOne('/api/v1/configuracoes/aceitar-termos');
    expect(pedido.request.method).toBe('POST');
    pedido.flush({ ...CONFIGURACAO_INICIAL, termos_aceites_em: '2026-09-24T10:00:00Z' });
    const estado = configuracoesReducer(initialState, emitidas[0]);
    expect(estado.configuracao.termos_aceites_em).toBe('2026-09-24T10:00:00Z');
  });
});
