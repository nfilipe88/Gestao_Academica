import { createAction, props } from '@ngrx/store';
import { FunilEtapa, OportunidadeCRM } from './crm.models';

export const carregarFunil = createAction('[CRM] Carregar Funil');
export const carregarFunilSucesso = createAction(
  '[CRM] Carregar Funil Sucesso',
  props<{ etapas: FunilEtapa[] }>()
);

export const carregarOportunidades = createAction('[CRM] Carregar Oportunidades');
export const carregarOportunidadesSucesso = createAction(
  '[CRM] Carregar Oportunidades Sucesso',
  props<{ oportunidades: OportunidadeCRM[] }>()
);

export const criarLead = createAction(
  '[CRM] Criar Lead',
  props<{
    nome_responsavel: string, email_contato: string | null, telefone: string | null,
    nome_aluno_candidato: string, data_nascimento_candidato: string | null, origem_lead: string
  }>()
);

export const atualizarLead = createAction(
  '[CRM] Atualizar Lead',
  props<{ lead_id: string, data_nascimento_candidato: string }>()
);

export const moverOportunidade = createAction(
  '[CRM] Mover Oportunidade',
  props<{ oportunidade_id: string, nova_etapa_id: string }>()
);

export const crmOperacaoSucesso = createAction(
  '[CRM] Operacao Sucesso',
  props<{ mensagem: string }>()
);

// Ação genérica de falha (mesmo padrão dos restantes módulos): sem isto,
// um erro HTTP dentro de um effect fica por apanhar e mata esse effect
// para o resto da sessão.
export const crmOperacaoFalhou = createAction(
  '[CRM API] Operação Falhou',
  props<{ erro: string }>()
);
