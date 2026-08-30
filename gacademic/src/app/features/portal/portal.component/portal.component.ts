import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, HostListener, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { Actions, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { filter, map, take } from 'rxjs';
import { selectUsuario } from '../../../store/auth/auth.selectors';
import { selectConfiguracao, selectMoeda } from '../../../store/configuracoes/configuracoes.selector';
import { MOEDAS_PAYPAL_SUPORTADAS } from '../../../store/configuracoes/configuracoes.models';
import { capturarPagamento, financeiroOperacaoSucesso, gerarCobranca } from '../../../store/financeiro/financeiro.actions';
import { selectUltimaCobranca } from '../../../store/financeiro/financeiro.selector';
import {
  carregarBoletimDoEducando, carregarExamesDoEducando, carregarFinanceiroDoEducando, carregarHorarioDoEducando,
  carregarMaterialDoEducando, carregarMateriaisDoEducando, carregarMeusEducandos, carregarResultadoExame,
  carregarTarefasDoEducando, iniciarTentativaExame, limparMaterialAberto, limparTentativaExame,
  perguntarProfVirtual, registarEventoSuspeito, submeterTentativaExame
} from '../../../store/portal/portal.actions';
import {
  selectAProcessarPerguntaProfVirtual, selectASubmeterTentativa, selectBoletimDoEducando, selectConversaProfVirtual,
  selectErroProfVirtual, selectEventosSuspeitosTentativa, selectExamesDoEducando, selectFinanceiroDoEducando,
  selectHorarioDoEducando, selectMaterialAberto, selectMateriaisDoEducando, selectMeusEducandos, selectPortalError,
  selectResultadoExame, selectTarefasDoEducando, selectTentativaAtual
} from '../../../store/portal/portal.selector';
import { HorarioAulaPortal } from '../../../store/portal/portal.models';
import * as DocumentosActions from '../../../store/documentos/documentos.actions';
import {
  selectDocumentosError, selectMinhasSolicitacoesEscola, selectPrecosDocumento,
  selectSolicitacoesEmissao, selectUltimaCobrancaDocumento
} from '../../../store/documentos/documentos.selector';
import { SolicitacaoDocumentoEmissao } from '../../../store/documentos/documentos.models';
import { abrirOuNavegar, abrirOuTransferirBlob } from '../../../core/utils/abrir-em-nova-aba';

// 1=Segunda ... 7=Domingo (ISO 8601), igual ao módulo Horários.
const DIAS_DA_SEMANA = [
  { valor: 1, nome: 'Segunda' },
  { valor: 2, nome: 'Terça' },
  { valor: 3, nome: 'Quarta' },
  { valor: 4, nome: 'Quinta' },
  { valor: 5, nome: 'Sexta' },
  { valor: 6, nome: 'Sábado' },
];

@Component({
  selector: 'app-portal.component',
  imports: [CommonModule, AsyncPipe, FormsModule],
  templateUrl: './portal.component.html',
  styleUrl: './portal.component.css',
})
export class PortalComponent implements OnInit {
  private store = inject(Store);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private actions$ = inject(Actions);
  private http = inject(HttpClient);

  usuario$ = this.store.select(selectUsuario);
  educandos$ = this.store.select(selectMeusEducandos);
  // Resumo consolidado — quem representa vários educandos vê logo
  // quantos têm propina em atraso, sem abrir o financeiro de cada um.
  educandosEmAtraso$ = this.educandos$.pipe(map(educandos => educandos.filter(e => e.tem_propina_em_atraso)));
  horario$ = this.store.select(selectHorarioDoEducando);
  boletim$ = this.store.select(selectBoletimDoEducando);
  financeiro$ = this.store.select(selectFinanceiroDoEducando);
  tarefas$ = this.store.select(selectTarefasDoEducando);
  materiais$ = this.store.select(selectMateriaisDoEducando);
  materialAberto$ = this.store.select(selectMaterialAberto);
  conversaProfVirtual$ = this.store.select(selectConversaProfVirtual);
  aProcessarPerguntaProfVirtual$ = this.store.select(selectAProcessarPerguntaProfVirtual);
  erroProfVirtual$ = this.store.select(selectErroProfVirtual);
  erro$ = this.store.select(selectPortalError);
  exames$ = this.store.select(selectExamesDoEducando);
  tentativaAtual$ = this.store.select(selectTentativaAtual);
  resultadoExame$ = this.store.select(selectResultadoExame);
  aSubmeterTentativa$ = this.store.select(selectASubmeterTentativa);
  eventosSuspeitosTentativa$ = this.store.select(selectEventosSuspeitosTentativa);

  precosDocumento$ = this.store.select(selectPrecosDocumento);
  solicitacoesDocumento$ = this.store.select(selectSolicitacoesEmissao);
  minhasSolicitacoesEscola$ = this.store.select(selectMinhasSolicitacoesEscola);
  erroDocumentos$ = this.store.select(selectDocumentosError);
  moeda$ = this.store.select(selectMoeda);
  iban$ = this.store.select(selectConfiguracao).pipe(map(c => c.iban));

  dias = DIAS_DA_SEMANA;

  educandoSelecionadoId: string | null = null;
  aba: 'horario' | 'boletim' | 'trabalhos' | 'materiais' | 'exames' | 'financeiro' | 'documentos' = 'horario';

  // Prof. Virtual — qual material está aberto e a pergunta a meio de escrever.
  materialAbertoId: string | null = null;
  perguntaAtual = '';

  // Exames online (LMS) — qual exame está a ser feito agora (mostra o
  // formulário de perguntas em vez da lista) e as respostas dadas até
  // ao momento; qual exame tem o resultado aberto (depois de submetido).
  exameEmCursoId: string | null = null;
  respostasTentativa: Record<string, string> = {};
  exameResultadoAbertoId: string | null = null;

  // Formulário "Novo pedido de documento"
  novoDocumentoTipo = 'CERTIFICADO';
  novoDocumentoFormato: 'DIGITAL' | 'FISICA' = 'DIGITAL';
  novoDocumentoDescricaoOutro = '';

  // Resposta a pedido da escola
  respostaEscolaAberta: string | null = null;
  textoRespostaEscola = '';

  ngOnInit() {
    this.store.dispatch(carregarMeusEducandos());
    this.store.dispatch(DocumentosActions.carregarPrecos());
    this.store.dispatch(DocumentosActions.carregarMinhasSolicitacoesEmissao());
    this.store.dispatch(DocumentosActions.carregarMinhasSolicitacoesEscola());

    // Depois do PayPal redirecionar de volta (return_url gerado em
    // POST /financeiro/faturas/{id}/gerar-cobranca ou em
    // POST /documentos/solicitacoes/{id}/gerar-cobranca, apontados para
    // cá quando quem paga é RESPONSAVEL/ALUNO), a página recarrega do
    // zero — o aluno_id (e, para documentos, tab=documentos) vêm na
    // própria URL para repormos a seleção.
    const params = this.route.snapshot.queryParamMap;
    const alunoId = params.get('aluno_id');
    const retorno = params.get('paypal_retorno');
    const token = params.get('token'); // PayPal chama o order_id de "token" no redirecionamento
    const tab = params.get('tab');

    if (alunoId) {
      this.onSelecionarEducando(alunoId);
    }
    if (tab === 'documentos') {
      this.aba = 'documentos';
    }
    if (retorno === 'sucesso' && token && tab === 'documentos') {
      this.store.dispatch(DocumentosActions.capturarPagamentoDocumento({ order_id: token }));
    } else if (retorno === 'sucesso' && token && alunoId) {
      this.financeiro$.pipe(filter(f => !!f?.contrato), take(1)).subscribe(financeiro => {
        this.store.dispatch(capturarPagamento({ order_id: token, contrato_id: financeiro!.contrato!.id }));
        // capturarPagamento$ só atualiza store/financeiro, não
        // store/portal — só refrescamos este depois de confirmado
        // (financeiroOperacaoSucesso), para não sobrepor com dados
        // ainda por capturar.
        this.actions$.pipe(ofType(financeiroOperacaoSucesso), take(1)).subscribe(() => {
          this.store.dispatch(carregarFinanceiroDoEducando({ aluno_id: alunoId }));
        });
      });
    }
    if (retorno) {
      this.router.navigate([], { relativeTo: this.route, queryParams: {}, replaceUrl: true });
    }
  }

  onSelecionarEducando(alunoId: string) {
    this.educandoSelecionadoId = alunoId;
    this.aba = 'horario';
    this.materialAbertoId = null;
    this.store.dispatch(carregarHorarioDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarBoletimDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarFinanceiroDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarTarefasDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarMateriaisDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarExamesDoEducando({ aluno_id: alunoId }));
    this.exameEmCursoId = null;
    this.exameResultadoAbertoId = null;
    this.store.dispatch(limparTentativaExame());
  }

  // --- Exames online (LMS) ---

  onIniciarExame(exameId: string) {
    if (!this.educandoSelecionadoId) return;
    this.exameEmCursoId = exameId;
    this.respostasTentativa = {};
    this.store.dispatch(iniciarTentativaExame({ aluno_id: this.educandoSelecionadoId, exame_id: exameId }));
  }

  onResponder(questaoId: string, valor: string) {
    this.respostasTentativa = { ...this.respostasTentativa, [questaoId]: valor };
  }

  onSubmeterExame() {
    if (!this.educandoSelecionadoId || !this.exameEmCursoId) return;
    this.store.dispatch(submeterTentativaExame({
      aluno_id: this.educandoSelecionadoId, exame_id: this.exameEmCursoId, respostas: this.respostasTentativa
    }));
    this.exameEmCursoId = null;
  }

  onSairDoExame() {
    this.exameEmCursoId = null;
    this.respostasTentativa = {};
    this.store.dispatch(limparTentativaExame());
  }

  // Proctoring básico: enquanto o aluno está a meio de uma tentativa
  // (exameEmCursoId definido), sair da aba/janela conta como evento
  // suspeito — nunca bloqueia o exame, só fica registado para o
  // professor rever ao corrigir (ver LMSResultadoAlunoExame). Não
  // dispara ao trocar de aba fora de um exame nem quando volta a
  // ficar visível (só na saída, para não contar o mesmo evento 2x).
  @HostListener('document:visibilitychange')
  onVisibilidadeMudou() {
    if (document.hidden && this.exameEmCursoId && this.educandoSelecionadoId) {
      this.store.dispatch(registarEventoSuspeito({ aluno_id: this.educandoSelecionadoId, exame_id: this.exameEmCursoId }));
    }
  }

  onVerResultadoExame(exameId: string) {
    if (!this.educandoSelecionadoId) return;
    this.exameResultadoAbertoId = this.exameResultadoAbertoId === exameId ? null : exameId;
    if (this.exameResultadoAbertoId) {
      this.store.dispatch(carregarResultadoExame({ aluno_id: this.educandoSelecionadoId, exame_id: exameId }));
    }
  }

  // --- Materiais de aula + Prof. Virtual ---

  onAbrirMaterial(materialId: string) {
    if (!this.educandoSelecionadoId) return;
    this.materialAbertoId = materialId;
    this.perguntaAtual = '';
    this.store.dispatch(carregarMaterialDoEducando({ aluno_id: this.educandoSelecionadoId, material_id: materialId }));
  }

  onFecharMaterial() {
    this.materialAbertoId = null;
    this.perguntaAtual = '';
    this.store.dispatch(limparMaterialAberto());
  }

  onEnviarPergunta() {
    const pergunta = this.perguntaAtual.trim();
    if (!pergunta || !this.educandoSelecionadoId || !this.materialAbertoId) return;

    // O histórico enviado é o que existia ANTES desta pergunta — o
    // reducer já acrescenta a pergunta atual ao conversaProfVirtual$
    // (ver PortalActions.perguntarProfVirtual), por isso capturamos o
    // valor com take(1) antes de despachar, não depois.
    this.conversaProfVirtual$.pipe(take(1)).subscribe(historico => {
      this.store.dispatch(perguntarProfVirtual({
        aluno_id: this.educandoSelecionadoId!,
        material_id: this.materialAbertoId!,
        historico,
        pergunta
      }));
    });
    this.perguntaAtual = '';
  }

  slotsDoDia(horarios: HorarioAulaPortal[] | null, dia: number): HorarioAulaPortal[] {
    if (!horarios) return [];
    return horarios.filter(h => h.dia_semana === dia).sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio));
  }

  formatarHora(hora: string): string {
    return hora?.substring(0, 5) ?? '';
  }

  // Mesmo padrão de financeiro.component.ts — o PayPal não aceita
  // todas as moedas (ex.: AOA/Kwanza), o botão só faz sentido mostrar-se
  // quando a moeda da escola está nessa lista.
  moedaSuportaPaypal(moeda: string | null): boolean {
    return !!moeda && MOEDAS_PAYPAL_SUPORTADAS.includes(moeda);
  }

  onDescarregarRecibo(faturaId: string) {
    const aba = window.open('', '_blank');
    this.http.get(`/api/v1/financeiro/faturas/${faturaId}/recibo`, { responseType: 'blob' }).subscribe({
      next: (blob) => abrirOuTransferirBlob(aba, blob, `recibo-${faturaId}.pdf`),
      error: () => { if (aba) aba.close(); }
    });
  }

  onPagarComPayPal(faturaId: string, contratoId: string) {
    // Abre já a aba em branco, de forma síncrona, dentro do próprio
    // handler de clique — é isto que impede o browser de bloquear como
    // pop-up. Só depois é que sabemos a approve_url (vem do back-end),
    // altura em que só falta redirecionar esta aba já aberta. Mesmo
    // padrão da página Financeiro (Gestor/Secretaria) — reaproveita a
    // mesma action/effect de gerarCobranca (já com o controlo de posse
    // no back-end, ver cruds/financeiro.py).
    const aba = window.open('', '_blank');
    this.store.dispatch(gerarCobranca({ fatura_id: faturaId, contrato_id: contratoId, metodo_pagamento: 'PAYPAL' }));

    this.store.select(selectUltimaCobranca).pipe(
      filter(cobranca => !!cobranca && cobranca.fatura_id === faturaId),
      take(1)
    ).subscribe(cobranca => {
      const approveUrl = cobranca?.dados_pagamento?.approve_url;
      if (approveUrl) {
        abrirOuNavegar(aba, approveUrl);
      } else if (aba) {
        aba.close();
      }
      // O effect gerarCobranca$ atualiza store/financeiro (usado pela
      // página do Gestor/Secretaria), não store/portal — sem isto, o
      // botão "Pagar com PayPal" não passava a "Continuar pagamento
      // PayPal" nesta página.
      if (this.educandoSelecionadoId) {
        this.store.dispatch(carregarFinanceiroDoEducando({ aluno_id: this.educandoSelecionadoId }));
      }
    });
  }

  // --- Documentos ---
  documentosDoEducando(solicitacoes: SolicitacaoDocumentoEmissao[] | null) {
    if (!solicitacoes || !this.educandoSelecionadoId) return [];
    return solicitacoes.filter(s => s.aluno_id === this.educandoSelecionadoId);
  }

  onCriarSolicitacaoDocumento() {
    if (!this.educandoSelecionadoId) return;
    this.store.dispatch(DocumentosActions.criarSolicitacaoEmissao({
      tipo_documento: this.novoDocumentoTipo, formato_entrega: this.novoDocumentoFormato,
      descricao_outro: this.novoDocumentoTipo === 'OUTRO' ? this.novoDocumentoDescricaoOutro : undefined,
      aluno_id: this.educandoSelecionadoId,
    }));
    this.novoDocumentoDescricaoOutro = '';
  }

  onPagarDocumentoComPayPal(solicitacaoId: string) {
    // Mesmo padrão de onPagarComPayPal: abre a aba já no clique para o
    // browser não bloquear como pop-up (a approve_url só chega depois,
    // de forma assíncrona).
    const aba = window.open('', '_blank');
    this.store.dispatch(DocumentosActions.gerarCobrancaDocumento({ solicitacao_id: solicitacaoId }));

    this.store.select(selectUltimaCobrancaDocumento).pipe(
      filter(cobranca => !!cobranca && cobranca.solicitacao_id === solicitacaoId),
      take(1)
    ).subscribe(cobranca => {
      const approveUrl = cobranca?.dados_pagamento?.approve_url;
      if (approveUrl) {
        abrirOuNavegar(aba, approveUrl);
      } else if (aba) {
        aba.close();
      }
    });
  }

  // Ver nota equivalente em documentos.component.ts::onVerPdf — um <a
  // href> normal não envia o Bearer token (não passa pelo
  // HttpClient/jwt.interceptor), por isso o PDF tem de ser pedido via
  // HttpClient e aberto como blob.
  onVerPdfDocumento(solicitacaoId: string) {
    const aba = window.open('', '_blank');
    this.http.get(`/api/v1/documentos/solicitacoes/${solicitacaoId}/pdf`, { responseType: 'blob' }).subscribe({
      next: (blob) => abrirOuTransferirBlob(aba, blob, `documento-${solicitacaoId}.pdf`),
      error: () => { if (aba) aba.close(); }
    });
  }

  // --- Pedidos da escola (respondo eu, ALUNO/RESPONSAVEL) ---
  onAbrirRespostaEscola(solicitacaoId: string) {
    this.respostaEscolaAberta = solicitacaoId;
    this.textoRespostaEscola = '';
  }

  onEnviarRespostaEscola(solicitacaoId: string) {
    if (!this.textoRespostaEscola.trim()) return;
    this.store.dispatch(DocumentosActions.responderSolicitacaoEscola({ solicitacao_id: solicitacaoId, resposta_texto: this.textoRespostaEscola }));
    this.respostaEscolaAberta = null;
  }
}
