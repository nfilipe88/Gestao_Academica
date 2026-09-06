import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { filter, map, switchMap, take } from 'rxjs';
import { selectIsGestor } from '../../store/auth/auth.selectors';
import { carregarConfiguracao } from '../../store/configuracoes/configuracoes.actions';
import { selectConfiguracao, selectConfiguracoesCarregada } from '../../store/configuracoes/configuracoes.selector';

// Força a passagem por Configurações antes de qualquer outra rota
// protegida, enquanto o Ano Letivo (data_inicio_ano_letivo /
// data_fim_ano_letivo) não estiver definido — pedido direto do
// utilizador: "depois de criar uma escola, o próximo passo obrigatório
// seria encaminhar para configurações da escola". Aplicado ao lado de
// authGuard na rota-pai da shell (ver app.routes.ts), corre em toda
// navegação protegida, não só na primeira.
export const configuracaoInicialGuard: CanActivateFn = (route, state) => {
  const store = inject(Store);
  const router = inject(Router);

  // Nunca bloquear as próprias /configuracoes (senão nunca lá chegava
  // para completar o setup) nem /perfil (o Gestor continua a poder
  // gerir a própria conta a meio deste setup).
  if (state.url.startsWith('/configuracoes') || state.url.startsWith('/perfil')) {
    return true;
  }

  return store.select(selectIsGestor).pipe(
    take(1),
    switchMap(isGestor => {
      // Só o Gestor consegue editar Configurações (PUT /api/v1/configuracoes
      // exige_perfil("GESTOR") no back-end) — forçar Secretaria/Professor/
      // Aluno/Responsável para uma página onde não conseguem submeter
      // nada não faz sentido, por isso passam sempre.
      if (!isGestor) return [true];

      // A Configuração pode ainda não ter chegado do back-end (a shell
      // dispara carregarConfiguracao() no arranque, mas este guard corre
      // ANTES dela montar) — despacha só se ainda não tiver sido
      // carregada (evita um pedido redundante em cada navegação) e
      // espera pela resposta em vez de decidir com dados que podem
      // ainda estar vazios.
      return store.select(selectConfiguracoesCarregada).pipe(
        take(1),
        switchMap(carregada => {
          if (!carregada) store.dispatch(carregarConfiguracao());
          return store.select(selectConfiguracoesCarregada).pipe(filter(c => c), take(1));
        }),
        switchMap(() => store.select(selectConfiguracao).pipe(take(1))),
        map(config => {
          if (config.data_inicio_ano_letivo && config.data_fim_ano_letivo) return true;
          return router.createUrlTree(['/configuracoes'], { queryParams: { setup: '1' } });
        })
      );
    })
  );
};
