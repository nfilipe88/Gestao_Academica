import { createAction, props } from '@ngrx/store';
import { Perfil } from './perfil.models';

export const carregarPerfil = createAction('[Perfil] Carregar Perfil');
export const carregarPerfilSucesso = createAction(
  '[Perfil] Carregar Perfil Sucesso',
  props<{ perfil: Perfil }>()
);

export const atualizarPerfil = createAction(
  '[Perfil] Atualizar Perfil',
  props<{ nome_completo: string; email: string }>()
);

export const alterarSenha = createAction(
  '[Perfil] Alterar Senha',
  props<{ senha_atual: string; nova_senha: string }>()
);

export const perfilOperacaoSucesso = createAction('[Perfil] Operacao Sucesso', props<{ mensagem: string }>());
export const perfilOperacaoFalhou = createAction('[Perfil API] Operação Falhou', props<{ erro: string }>());

// Limpa mensagem/erro ao sair do ecrã ou ao começar uma nova submissão
// — sem isto, uma mensagem de sucesso da alteração de nome ficava
// visível depois de ir tentar mudar a senha, por exemplo.
export const limparMensagensPerfil = createAction('[Perfil] Limpar Mensagens');
