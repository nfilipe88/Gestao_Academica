import { defer, distinctUntilChanged, EMPTY, fromEvent, map, Observable, of, repeat, startWith, switchMap, timer, catchError } from 'rxjs';

export type ResultadoPolling<T> = { ok: true; valor: T } | { ok: false; erro: unknown };

export interface OpcoesPolling {
  /** Intervalo normal entre pedidos (ms). */
  base?: number;
  /** Teto do intervalo depois de falhas seguidas (ms). */
  maximo?: number;
  /** Variação aleatória do intervalo (0,2 = ±20%) — evita que milhares de separadores peçam todos no mesmo segundo. */
  jitter?: number;
  aleatorio?: () => number;
  /** true = separador visível. Por omissão segue o Page Visibility API. */
  visivel$?: Observable<boolean>;
}

/** Emite true/false conforme o separador está visível ou escondido (minimizado, outro separador…). */
export function visibilidadeDoDocumento$(doc: Document): Observable<boolean> {
  return fromEvent(doc, 'visibilitychange').pipe(
    map(() => doc.visibilityState === 'visible'),
    startWith(doc.visibilityState === 'visible'),
  );
}

/**
 * Pergunta periodicamente ao servidor (ex.: nº de notificações por ler) sem o
 * sobrecarregar:
 *  - SÓ pede enquanto o separador está visível; ao voltar a ficar visível pede
 *    logo (o utilizador vê o valor atualizado sem esperar pelo intervalo);
 *  - variação aleatória (jitter) no intervalo;
 *  - recuo exponencial depois de falhas (base×2, ×4… até ao máximo) e regresso
 *    ao intervalo normal ao primeiro sucesso.
 * Nunca termina sozinho: quem chama pára-o com takeUntil (logout, etc.).
 */
export function pollingContagem<T>(pedir: () => Observable<T>, opcoes: OpcoesPolling & { visivel$: Observable<boolean> }): Observable<ResultadoPolling<T>> {
  const base = opcoes.base ?? 60_000;
  const maximo = opcoes.maximo ?? 300_000;
  const jitter = opcoes.jitter ?? 0.2;
  const aleatorio = opcoes.aleatorio ?? Math.random;

  return opcoes.visivel$.pipe(
    distinctUntilChanged(),
    switchMap(visivel => {
      if (!visivel) return EMPTY;
      let falhas = 0;
      const atraso = () => {
        const alvo = Math.min(base * 2 ** falhas, maximo);
        return Math.round(alvo * (1 + (aleatorio() * 2 - 1) * jitter));
      };
      return defer(() => pedir().pipe(
        map((valor): ResultadoPolling<T> => { falhas = 0; return { ok: true, valor }; }),
        catchError(erro => { falhas++; return of<ResultadoPolling<T>>({ ok: false, erro }); }),
      )).pipe(repeat({ delay: () => timer(atraso()) }));
    }),
  );
}
