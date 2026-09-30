import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, inject, OnDestroy, OnInit, PLATFORM_ID, signal, ViewChild } from '@angular/core';
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CHAVE_SESSAO_PORTAL_EDUCANDO, guardarSessao, lerSessao } from '../../../core/utils/armazenamento-sessao';
import { CHAVE_LOCAL_DICAS_PORTAL_FECHADAS, guardarLocal, lerLocal } from '../../../core/utils/armazenamento-local';
import { Actions, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { combineLatest, filter, map, take } from 'rxjs';
import { selectUsuario } from '../../../store/auth/auth.selectors';
import { selectConfiguracao, selectMoeda } from '../../../store/configuracoes/configuracoes.selector';
import { MOEDAS_PAYPAL_SUPORTADAS } from '../../../store/configuracoes/configuracoes.models';
import { capturarPagamento, financeiroOperacaoSucesso, gerarCobranca, reportarPagamentoFatura } from '../../../store/financeiro/financeiro.actions';
import { selectUltimaCobranca } from '../../../store/financeiro/financeiro.selector';
import {
  carregarBoletimDoEducando, carregarComunicadosDoEducando, carregarEstatisticasDoEducando, carregarExamesDoEducando,
  carregarFinanceiroDoEducando, carregarHorarioDoEducando, carregarMaterialDoEducando, carregarMateriaisDoEducando,
  carregarMeusEducandos, carregarPautaDoEducando, carregarResultadoExame, carregarTarefasDoEducando,
  iniciarTentativaExame, limparMaterialAberto, limparTentativaExame, perguntarProfVirtual, registarEventoSuspeito,
  registarViolacaoDispositivo, reportarSinalFoco, responderComunicado, responderComunicadoSucesso, submeterTentativaExame
} from '../../../store/portal/portal.actions';
import {
  selectAProcessarPerguntaProfVirtual, selectASubmeterTentativa, selectBoletimDoEducando,
  selectComunicadosDoEducando, selectConversaProfVirtual, selectErroProfVirtual, selectEstatisticasDoEducando,
  selectEventosSuspeitosTentativa, selectExamesDoEducando, selectFinanceiroDoEducando, selectHorarioDoEducando,
  selectMaterialAberto, selectMateriaisDoEducando, selectMeusEducandos, selectPautaDoEducando, selectPortalError,
  selectResultadoExame, selectTarefasDoEducando, selectTentativaAtual
} from '../../../store/portal/portal.selector';
import { EducandoResumo, ExameEducando, HorarioAulaPortal } from '../../../store/portal/portal.models';
import { PautaTabelaComponent } from '../pauta-tabela/pauta-tabela.component';
import { FotoPerfilAluno } from '../../../store/alunos/alunos.models';
import * as DocumentosActions from '../../../store/documentos/documentos.actions';
import {
  selectDocumentosError, selectMinhasSolicitacoesEscola, selectPrecosDocumentoDisponiveis,
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
  imports: [CommonModule, AsyncPipe, FormsModule, RouterLink, PautaTabelaComponent],
  templateUrl: './portal.component.html',
  styleUrl: './portal.component.css',
})
export class PortalComponent implements OnInit, OnDestroy {
  private store = inject(Store);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private actions$ = inject(Actions);
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);

  usuario$ = this.store.select(selectUsuario);
  educandos$ = this.store.select(selectMeusEducandos);
  // Resumo consolidado — quem representa vários educandos vê logo
  // quantos têm propina em atraso, sem abrir o financeiro de cada um.
  educandosEmAtraso$ = this.educandos$.pipe(map(educandos => educandos.filter(e => e.tem_propina_em_atraso)));
  horario$ = this.store.select(selectHorarioDoEducando);
  boletim$ = this.store.select(selectBoletimDoEducando);
  pauta$ = this.store.select(selectPautaDoEducando);
  // Colunas da tabela da Pauta: união dos nomes de período de todas as
  // disciplinas, na ordem em que aparecem primeiro (cada disciplina já
  // vem ordenada cronologicamente do back-end — ver
  // cruds/portal.py::obter_pauta_do_educando).
  pautaColunas$ = this.pauta$.pipe(map(pauta => {
    const nomes: string[] = [];
    for (const disciplina of pauta?.disciplinas ?? []) {
      for (const periodo of disciplina.periodos) {
        if (!nomes.includes(periodo.periodo_avaliacao)) nomes.push(periodo.periodo_avaliacao);
      }
    }
    return nomes;
  }));
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
  estatisticas$ = this.store.select(selectEstatisticasDoEducando);
  comunicados$ = this.store.select(selectComunicadosDoEducando);

  precosDocumento$ = this.store.select(selectPrecosDocumentoDisponiveis);
  solicitacoesDocumento$ = this.store.select(selectSolicitacoesEmissao);
  minhasSolicitacoesEscola$ = this.store.select(selectMinhasSolicitacoesEscola);
  erroDocumentos$ = this.store.select(selectDocumentosError);
  moeda$ = this.store.select(selectMoeda);
  iban$ = this.store.select(selectConfiguracao).pipe(map(c => c.iban));

  // Sugestões do que explorar no separador Dashboard — pedido direto do
  // utilizador (ver mesma docstring em dashboard-home.component.ts).
  // Um único conjunto de dicas serve Aluno e Responsável (mesmas
  // ações fazem sentido para ambos); painel dispensável, preferência
  // guardada em localStorage (ver core/utils/armazenamento-local.ts).
  dicasFechadas = signal(lerLocal(this.platformId, CHAVE_LOCAL_DICAS_PORTAL_FECHADAS) === '1');

  fecharDicas() {
    this.dicasFechadas.set(true);
    guardarLocal(this.platformId, CHAVE_LOCAL_DICAS_PORTAL_FECHADAS, '1');
  }

  dias = DIAS_DA_SEMANA;

  educandoSelecionadoId: string | null = null;
  // Os separadores deixaram de ser um tab-bar dentro da página — agora
  // são entradas próprias no menu lateral (ver dashboard-layout.component.html),
  // todas apontando para /portal com um query param ?tab= diferente.
  // Continuam a partilhar a MESMA instância do componente (mesma rota,
  // só o query param muda), por isso o educando selecionado e os dados
  // já carregados sobrevivem a trocar de separador — só este campo
  // precisa de acompanhar a URL, feito abaixo em ngOnInit.
  readonly ABAS_VALIDAS = ['dashboard', 'horario', 'boletim', 'pauta', 'trabalhos', 'materiais', 'exames', 'financeiro', 'documentos', 'comunicados'] as const;
  aba: 'dashboard' | 'horario' | 'boletim' | 'pauta' | 'trabalhos' | 'materiais' | 'exames' | 'financeiro' | 'documentos' | 'comunicados' = 'dashboard';

  // Rematrícula self-service — estado local do pedido em curso, para o
  // botão mostrar "A enviar..." e não deixar clicar duas vezes.
  aEnviarPedidoRematricula = false;
  erroRematricula: string | null = null;

  // Transferência/Reingresso cross-escola self-service — mesmo
  // mecanismo de sempre (POST /transferencias), só que a partir do
  // Portal e restrito aos próprios educandos (ver
  // cruds/portal.py::pedir_transferencia).
  //
  // signal() e não propriedades simples de propósito: as mutações
  // abaixo acontecem dentro do callback .subscribe() de uma chamada
  // HTTP — nesta app zoneless, isso só passa a re-render se for escrita
  // de signal (um clique síncrono já dispara deteção sozinho; o que
  // acontece DEPOIS, quando a resposta HTTP chega, não).
  mostrarFormularioTransferencia = signal(false);
  nifDestinoTransferencia = signal('');
  motivoTransferencia = signal('');
  aEnviarPedidoTransferencia = signal(false);
  erroTransferencia = signal<string | null>(null);
  mensagemTransferencia = signal<string | null>(null);

  // Foto de perfil do educando — a que vale para o cartão de acesso
  // (ver app/database/models_pessoas.py::FotoPerfilAluno). Deve ser
  // renovada todos os anos; a antiga fica arquivada.
  fotosPerfilEducando = signal<FotoPerfilAluno[]>([]);
  fotoPerfilAEnviar = signal(false);
  erroFotoPerfil = signal<string | null>(null);

  // Prof. Virtual — qual material está aberto e a pergunta a meio de escrever.
  materialAbertoId: string | null = null;
  perguntaAtual = '';

  // Exames online (LMS) — qual exame está a ser feito agora (mostra o
  // formulário de perguntas em vez da lista) e as respostas dadas até
  // ao momento; qual exame tem o resultado aberto (depois de submetido).
  // signal() — precisa de ser escrito também dentro do callback
  // assíncrono de getUserMedia (ver pedirPermissaoEComecar), não só em
  // cliques síncronos.
  exameEmCursoId = signal<string | null>(null);
  respostasTentativa: Record<string, string> = {};
  exameResultadoAbertoId: string | null = null;

  // Ecrã de permissão de câmara/microfone — só existe entre clicar
  // "Começar"/"Continuar" num exame que exige câmara e/ou microfone e
  // conseguir mesmo o stream (ou desistir). signal() porque é escrito
  // dentro do callback assíncrono de getUserMedia, não de um clique
  // síncrono — numa app zoneless isso não re-renderiza sozinho sem ser
  // um signal (mesmo cuidado já documentado acima em mostrarFormularioTransferencia).
  exameASerIniciado = signal<ExameEducando | null>(null);
  aPedirPermissaoCamera = signal(false);
  erroPermissaoCamera = signal<string | null>(null);
  // Controla só a presença do <video> de auto-visualização no template
  // (precisa de ser signal — é ligado dentro do callback assíncrono de
  // getUserMedia, não de um clique síncrono; ver nota acima sobre
  // zoneless). O MediaStream em si fica num campo simples, nunca lido
  // reativamente.
  streamCameraAtivo = signal(false);
  @ViewChild('videoAutoVisualizacao') videoAutoVisualizacaoRef?: ElementRef<HTMLVideoElement>;
  private streamCameraExame: MediaStream | null = null;

  // Deteção de foco (Fatia 3) — indicador ao vivo, puramente local
  // (nunca fica reativo à espera do back-end); os detalhes do ciclo em
  // si (FaceLandmarker, intervalos) vivem nos campos privados abaixo.
  focoAoVivo = signal<boolean | null>(null);
  private faceLandmarker: FaceLandmarker | null = null;
  private cicloDeteccaoFoco: ReturnType<typeof setInterval> | null = null;
  private cicloEnvioFoco: ReturnType<typeof setInterval> | null = null;
  private amostrasFocoAcumuladas = { focado: 0, totais: 0 };

  // Formulário "Novo pedido de documento" — o valor de novoDocumentoTipo
  // é reposto (ver ngOnInit) assim que precosDocumento$ chega, para
  // nunca ficar preso num tipo que esta escola não ativou (o <select>
  // só lista os tipos ativos; um valor por omissão fixo aqui podia não
  // corresponder a nenhuma <option> real e o pedido falhava com "não
  // está disponível", mesmo o utilizador nunca tendo tocado no campo).
  novoDocumentoTipo = '';
  novoDocumentoFormato: 'DIGITAL' | 'FISICA' = 'DIGITAL';
  novoDocumentoDescricaoOutro = '';

  // Resposta a pedido da escola
  respostaEscolaAberta: string | null = null;
  textoRespostaEscola = '';

  // Resposta a um Comunicado — fecha logo ao submeter (otimista); o
  // conjunto de "já respondidos" é um signal porque só muda dentro do
  // callback assíncrono de responderComunicadoSucesso (ver
  // onEnviarRespostaComunicado), fora do que o CD zoneless já rastreia
  // sozinho num campo simples.
  respostaComunicadoAberta: string | null = null;
  textoRespostaComunicado = '';
  comunicadosRespondidos = signal<Set<string>>(new Set());

  ngOnInit() {
    this.store.dispatch(carregarMeusEducandos());
    this.store.dispatch(DocumentosActions.carregarPrecosDisponiveis());
    this.store.dispatch(DocumentosActions.carregarMinhasSolicitacoesEmissao());
    this.store.dispatch(DocumentosActions.carregarMinhasSolicitacoesEscola());

    // Assim que a lista real chega, garante que novoDocumentoTipo
    // aponta para um tipo que esta escola realmente ativou — nunca
    // fica preso vazio nem num tipo inexistente na lista.
    this.precosDocumento$.subscribe(precos => {
      if (precos.length && !precos.some(p => p.tipo_documento === this.novoDocumentoTipo)) {
        this.novoDocumentoTipo = precos[0].tipo_documento;
      }
    });

    // Assim que uma tentativa é marcada anulada (saiu da página,
    // câmara/microfone desligado a meio) — pára logo a câmara e o
    // ciclo de deteção de foco, em vez de ficarem ligados até o aluno
    // clicar "Voltar à lista" à mão.
    this.tentativaAtual$.subscribe(tentativa => {
      if (tentativa?.anulada) this.pararStreamCamera();
    });

    // Separador ativo acompanha o query param ?tab= — agora que os
    // separadores são entradas do menu lateral (routerLink para /portal
    // com um ?tab= diferente cada), em vez de um tab-bar dentro da
    // página. Subscrição (não só o snapshot inicial) porque a mesma
    // instância do componente fica viva ao navegar entre separadores
    // (mesma rota, só o query param muda) — isto também cobre o valor
    // inicial, já que ActivatedRoute.queryParamMap emite logo ao
    // subscrever.
    this.route.queryParamMap.subscribe(qp => {
      const tabAtual = qp.get('tab');
      this.aba = (tabAtual && (this.ABAS_VALIDAS as readonly string[]).includes(tabAtual))
        ? tabAtual as typeof this.aba : 'dashboard';
    });

    // aluno_id: primeiro a URL (depois do PayPal redirecionar de volta —
    // return_url gerado em POST /financeiro/faturas/{id}/gerar-cobranca
    // ou em POST /documentos/solicitacoes/{id}/gerar-cobranca, apontados
    // para cá quando quem paga é RESPONSAVEL/ALUNO — ou de um link
    // direto), senão o que ficou guardado nesta aba (sessionStorage) da
    // última vez — sem isto, trocar de separador do menu (nova
    // navegação para /portal, só o ?tab= muda) ou voltar mais tarde
    // esquecia sempre qual educando estava selecionado (achado real de
    // uma auditoria de UX desta sessão).
    const params = this.route.snapshot.queryParamMap;
    const alunoId = params.get('aluno_id') || lerSessao(this.platformId, CHAVE_SESSAO_PORTAL_EDUCANDO);
    const retorno = params.get('paypal_retorno');
    const token = params.get('token'); // PayPal chama o order_id de "token" no redirecionamento
    const tab = params.get('tab');

    if (alunoId) {
      this.onSelecionarEducando(alunoId);
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
      // Limpa aluno_id/paypal_retorno/token da URL (já foram lidos
      // acima), mas preserva o separador — sem isto, a navegação para
      // "limpar" a URL fazia a subscrição do tab acima recuar para
      // "dashboard" logo a seguir a mostrar corretamente "documentos".
      this.router.navigate([], { relativeTo: this.route, queryParams: tab === 'documentos' ? { tab: 'documentos' } : {}, replaceUrl: true });
    }

    // Login ALUNO só tem UM educando possível (ele próprio) — nunca faz
    // sentido obrigá-lo a escolher-se a si mesmo, ao contrário de
    // RESPONSAVEL (0, 1 ou vários filhos, ver template). Complementa o
    // restauro por URL/sessionStorage acima, nunca o substitui — só
    // atua quando nada foi restaurado (!educandoSelecionadoId), por
    // isso não interfere com o retorno do PayPal nem com trocar de
    // separador (mesma instância do componente, este take(1) já não
    // volta a disparar depois da primeira vez).
    combineLatest([this.usuario$, this.educandos$]).pipe(
      filter(([usuario, educandos]) => usuario?.perfil_acesso === 'ALUNO' && educandos.length === 1 && !this.educandoSelecionadoId),
      take(1)
    ).subscribe(([, educandos]) => this.onSelecionarEducando(educandos[0].aluno_id));
  }

  // Objeto completo do educando atualmente selecionado — o <select>
  // só guarda o id (educandoSelecionadoId); usado pelo cartão de
  // Rematrícula, que precisa dos vários campos elegivel_rematricula/
  // bloqueado_rematricula_por_atraso/etc.
  educandoAtual(educandos: EducandoResumo[] | null): EducandoResumo | undefined {
    return educandos?.find(e => e.aluno_id === this.educandoSelecionadoId);
  }

  onPedirRematricula(alunoId: string) {
    this.aEnviarPedidoRematricula = true;
    this.erroRematricula = null;
    this.http.post(`/api/v1/portal/educandos/${alunoId}/pedir-rematricula`, {}).subscribe({
      next: () => {
        this.aEnviarPedidoRematricula = false;
        this.store.dispatch(carregarMeusEducandos()); // repõe pedido_rematricula_confirmado
      },
      error: (err) => {
        this.aEnviarPedidoRematricula = false;
        this.erroRematricula = err.error?.detail || 'Não foi possível enviar o pedido de rematrícula.';
      },
    });
  }

  onPedirTransferencia(alunoId: string) {
    const nif = this.nifDestinoTransferencia().trim();
    if (!nif) return;
    this.aEnviarPedidoTransferencia.set(true);
    this.erroTransferencia.set(null);
    this.http.post(`/api/v1/portal/educandos/${alunoId}/pedir-transferencia`, {
      nif_destino: nif, motivo: this.motivoTransferencia().trim() || null,
    }).subscribe({
      next: () => {
        this.aEnviarPedidoTransferencia.set(false);
        this.mostrarFormularioTransferencia.set(false);
        this.nifDestinoTransferencia.set('');
        this.motivoTransferencia.set('');
        this.mensagemTransferencia.set('Pedido enviado — a instituição de destino vai decidir diretamente.');
      },
      error: (err) => {
        this.aEnviarPedidoTransferencia.set(false);
        this.erroTransferencia.set(err.error?.detail || 'Não foi possível enviar o pedido de transferência.');
      },
    });
  }

  onSelecionarEducando(alunoId: string) {
    this.educandoSelecionadoId = alunoId;
    // NÃO mexer em this.aba aqui — é derivado do query param ?tab= (ver
    // a subscrição a queryParamMap no ngOnInit) e um separador é uma
    // entrada do menu lateral, não um estado por-educando. Escrever
    // aqui diretamente ficava fora de sincronia com o URL e com o
    // separador realçado no menu: trocar de educando a meio do
    // Boletim/Documentos/etc. saltava silenciosamente para o
    // Dashboard, sem o URL nem o menu lateral acompanharem.
    this.erroRematricula = null;
    this.erroTransferencia.set(null);
    this.mostrarFormularioTransferencia.set(false);
    this.materialAbertoId = null;
    this.store.dispatch(carregarHorarioDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarBoletimDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarPautaDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarFinanceiroDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarTarefasDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarMateriaisDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarExamesDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarEstatisticasDoEducando({ aluno_id: alunoId }));
    this.store.dispatch(carregarComunicadosDoEducando({ aluno_id: alunoId }));
    this.exameEmCursoId.set(null);
    this.exameResultadoAbertoId = null;
    this.store.dispatch(limparTentativaExame());
    this.carregarFotosPerfil(alunoId);

    // Espelha a escolha no URL (?aluno_id=..., sobrevive a F5/link
    // direto — merge preserva o resto da query string, ex.:
    // tab=financeiro) e no sessionStorage (sobrevive também a trocar
    // de separador do menu lateral e voltar, mesmo sem o aluno_id no
    // URL nesse momento — ver ngOnInit).
    this.router.navigate([], {
      relativeTo: this.route, queryParams: { aluno_id: alunoId }, queryParamsHandling: 'merge', replaceUrl: true
    });
    guardarSessao(this.platformId, CHAVE_SESSAO_PORTAL_EDUCANDO, alunoId);
  }

  // Troca de Ano Letivo no separador Pauta — só ali, o Dashboard
  // mostra sempre o ano corrente (ver pauta$, carregado sem ano_letivo
  // em onSelecionarEducando acima).
  onSelecionarAnoLetivoPauta(anoLetivo: string) {
    if (!this.educandoSelecionadoId) return;
    this.store.dispatch(carregarPautaDoEducando({ aluno_id: this.educandoSelecionadoId, ano_letivo: Number(anoLetivo) }));
  }

  // --- Foto de perfil (self-service) ---

  private carregarFotosPerfil(alunoId: string) {
    this.erroFotoPerfil.set(null);
    this.http.get<FotoPerfilAluno[]>(`/api/v1/portal/educandos/${alunoId}/fotos-perfil`).subscribe({
      next: (fotos) => this.fotosPerfilEducando.set(fotos),
    });
  }

  onSelecionarFotoPerfil(evento: Event, alunoId: string) {
    const ficheiro = (evento.target as HTMLInputElement).files?.[0];
    if (!ficheiro) return;
    const dados = new FormData();
    dados.append('ficheiro', ficheiro);
    this.fotoPerfilAEnviar.set(true);
    this.erroFotoPerfil.set(null);
    this.http.post<{ fotos: FotoPerfilAluno[] }>(`/api/v1/portal/educandos/${alunoId}/foto-perfil`, dados).subscribe({
      next: (resp) => {
        this.fotoPerfilAEnviar.set(false);
        this.fotosPerfilEducando.set(resp.fotos);
      },
      error: (err) => {
        this.fotoPerfilAEnviar.set(false);
        this.erroFotoPerfil.set(err.error?.detail || 'Não foi possível enviar a fotografia.');
      },
    });
    (evento.target as HTMLInputElement).value = '';
  }

  onVerFotoPerfil(alunoId: string, fotoId: string) {
    const janela = window.open('', '_blank');
    this.http.get<{ url: string }>(`/api/v1/portal/educandos/${alunoId}/fotos-perfil/${fotoId}/url`).subscribe({
      next: (resp) => {
        janela?.document.write(`<img src="${resp.url}" style="max-width:100%;max-height:100vh;display:block;margin:0 auto">`);
      },
      error: () => janela?.close(),
    });
  }

  onVerCartaoAcesso(alunoId: string) {
    const aba = window.open('', '_blank');
    this.http.get(`/api/v1/portal/educandos/${alunoId}/cartao-acesso.pdf`, { responseType: 'blob' }).subscribe({
      next: (blob) => abrirOuTransferirBlob(aba, blob, `cartao-acesso-${alunoId}.pdf`),
      error: () => { if (aba) aba.close(); }
    });
  }

  // --- Exames online (LMS) ---

  onIniciarExame(exame: ExameEducando) {
    if (!this.educandoSelecionadoId) return;
    if (!exame.exigir_camera && !exame.exigir_microfone) {
      this.comecarTentativa(exame.id);
      return;
    }
    // Exige câmara/microfone — pede a permissão ANTES de sequer
    // contactar o back-end; só ao conceder é que o exame começa mesmo
    // (ver docstring de LMSExame.exigir_camera).
    this.exameASerIniciado.set(exame);
    this.erroPermissaoCamera.set(null);
    this.pedirPermissaoEComecar(exame);
  }

  private async pedirPermissaoEComecar(exame: ExameEducando) {
    this.aPedirPermissaoCamera.set(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: exame.exigir_camera, audio: exame.exigir_microfone
      });
      this.streamCameraExame = stream;
      this.streamCameraAtivo.set(true);
      // Se uma track obrigatória parar a meio (permissão revogada,
      // dispositivo desligado fisicamente) — ver onTrackObrigatoriaParou.
      for (const track of stream.getVideoTracks()) {
        track.addEventListener('ended', () => this.onTrackObrigatoriaParou('camera'));
      }
      for (const track of stream.getAudioTracks()) {
        track.addEventListener('ended', () => this.onTrackObrigatoriaParou('microfone'));
      }
      this.exameASerIniciado.set(null);
      this.aPedirPermissaoCamera.set(false);
      this.comecarTentativa(exame.id);
      // Aguarda o próximo ciclo de render para o <video> de
      // auto-visualização existir no DOM (só aparece depois de
      // exameEmCursoId ficar preenchido em comecarTentativa).
      queueMicrotask(() => {
        this.ligarAutoVisualizacao();
        // Só faz sentido detetar foco quando há vídeo para analisar —
        // um exame que só exige microfone não tem imagem nenhuma.
        if (exame.exigir_camera) this.iniciarCicloDeDeteccaoDeFoco(exame.id);
      });
    } catch {
      this.aPedirPermissaoCamera.set(false);
      const partes = [
        exame.exigir_camera ? 'câmara' : null,
        exame.exigir_microfone ? 'microfone' : null,
      ].filter(Boolean).join(' e ');
      this.erroPermissaoCamera.set(
        `Este exame exige ${partes} ativo(a). Conceda a permissão no browser para continuar.`
      );
    }
  }

  private ligarAutoVisualizacao() {
    if (this.videoAutoVisualizacaoRef && this.streamCameraExame) {
      this.videoAutoVisualizacaoRef.nativeElement.srcObject = this.streamCameraExame;
    }
  }

  onCancelarPermissaoCamera() {
    this.exameASerIniciado.set(null);
    this.erroPermissaoCamera.set(null);
    this.pararStreamCamera();
  }

  onTentarPermissaoCameraOutraVez() {
    const exame = this.exameASerIniciado();
    if (exame) {
      this.erroPermissaoCamera.set(null);
      this.pedirPermissaoEComecar(exame);
    }
  }

  private comecarTentativa(exameId: string) {
    if (!this.educandoSelecionadoId) return;
    this.exameEmCursoId.set(exameId);
    this.respostasTentativa = {};
    this.store.dispatch(iniciarTentativaExame({ aluno_id: this.educandoSelecionadoId, exame_id: exameId }));
  }

  private pararStreamCamera() {
    this.streamCameraExame?.getTracks().forEach(track => track.stop());
    this.streamCameraExame = null;
    this.streamCameraAtivo.set(false);
    this.pararCicloDeDeteccaoDeFoco();
  }

  // ------------------------------------------------------------------
  // Deteção de foco (rosto orientado para o ecrã) — corre inteiramente
  // no browser (WASM, @mediapipe/tasks-vision), nunca envia vídeo/
  // imagem nenhuma para o servidor: só as contagens já agregadas (ver
  // reportarSinalFoco). "Focado" aqui é deliberadamente simples —
  // apenas se um rosto foi reconhecido no enquadramento — em vez de
  // rastreio fino do ângulo da cabeça, que precisaria de calibração
  // real contra câmaras a sério para não ficar cheio de falsos
  // positivos/negativos. Continua a apanhar o sinal que mais importa
  // na prática: o aluno saiu do enquadramento ou virou-se demasiado.
  // ------------------------------------------------------------------
  private async obterFaceLandmarker(): Promise<FaceLandmarker | null> {
    if (this.faceLandmarker) return this.faceLandmarker;
    try {
      const fileset = await FilesetResolver.forVisionTasks('/assets/mediapipe-wasm');
      this.faceLandmarker = await FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: '/assets/face_landmarker.task', delegate: 'GPU' },
        runningMode: 'VIDEO',
        numFaces: 1,
      });
      return this.faceLandmarker;
    } catch {
      // Sem WebGPU/WebGL, modelo a falhar a carregar, etc. — a deteção
      // de foco é só um extra informativo, nunca pode impedir o aluno
      // de fazer o exame por causa disto.
      return null;
    }
  }

  private async iniciarCicloDeDeteccaoDeFoco(exameId: string) {
    const landmarker = await this.obterFaceLandmarker();
    const video = this.videoAutoVisualizacaoRef?.nativeElement;
    if (!landmarker || !video) return;

    this.amostrasFocoAcumuladas = { focado: 0, totais: 0 };
    this.cicloDeteccaoFoco = setInterval(() => {
      if (video.readyState < 2) return; // ainda sem frame nenhum pronto
      const resultado = landmarker.detectForVideo(video, performance.now());
      const focado = resultado.faceLandmarks.length > 0;
      this.amostrasFocoAcumuladas.totais++;
      if (focado) this.amostrasFocoAcumuladas.focado++;
      this.focoAoVivo.set(focado);
    }, 1000);

    // Lote enviado periodicamente (não amostra a amostra) — mesmo
    // espírito de "custo real por chamada" já aplicado a outros sinais.
    this.cicloEnvioFoco = setInterval(() => this.enviarLoteDeFoco(exameId), 15_000);
  }

  private enviarLoteDeFoco(exameId: string) {
    const { focado, totais } = this.amostrasFocoAcumuladas;
    if (totais === 0 || !this.educandoSelecionadoId) return;
    this.amostrasFocoAcumuladas = { focado: 0, totais: 0 };
    this.store.dispatch(reportarSinalFoco({
      aluno_id: this.educandoSelecionadoId, exame_id: exameId, amostras_focado: focado, amostras_totais: totais
    }));
  }

  private pararCicloDeDeteccaoDeFoco() {
    if (this.cicloDeteccaoFoco !== null) clearInterval(this.cicloDeteccaoFoco);
    if (this.cicloEnvioFoco !== null) clearInterval(this.cicloEnvioFoco);
    this.cicloDeteccaoFoco = null;
    this.cicloEnvioFoco = null;
    this.focoAoVivo.set(null);
  }

  ngOnDestroy() {
    this.pararStreamCamera();
    this.faceLandmarker?.close();
  }

  onResponder(questaoId: string, valor: string) {
    this.respostasTentativa = { ...this.respostasTentativa, [questaoId]: valor };
  }

  onSubmeterExame() {
    const exameId = this.exameEmCursoId();
    if (!this.educandoSelecionadoId || !exameId) return;
    const alunoId = this.educandoSelecionadoId;
    this.store.dispatch(submeterTentativaExame({ aluno_id: alunoId, exame_id: exameId, respostas: this.respostasTentativa }));
    this.encerrarSessaoDeExame();
    this.store.dispatch(carregarExamesDoEducando({ aluno_id: alunoId }));
  }

  onSairDoExame() {
    this.encerrarSessaoDeExame();
    this.store.dispatch(limparTentativaExame());
    // Sem isto, a lista mostrava "Começar" para um exame já anulado até
    // a próxima recarga da página inteira — a store da lista só é
    // preenchida na entrada no separador, nunca ao sair de um exame.
    if (this.educandoSelecionadoId) {
      this.store.dispatch(carregarExamesDoEducando({ aluno_id: this.educandoSelecionadoId }));
    }
  }

  // Chamado ao sair da vista do exame por qualquer via (submeter,
  // "Sair", ou tentativa anulada) — pára a câmara/microfone e o ciclo
  // de deteção de foco, quando existirem.
  private encerrarSessaoDeExame() {
    const exameId = this.exameEmCursoId();
    // Envia o que sobrou por enviar antes de parar o ciclo — sem isto,
    // o último lote (até 15s de amostras) perdia-se sempre que o
    // aluno submetia/saía antes do próximo envio periódico.
    if (exameId) this.enviarLoteDeFoco(exameId);
    this.exameEmCursoId.set(null);
    this.respostasTentativa = {};
    this.pararStreamCamera();
  }

  // Proctoring: enquanto o aluno está a meio de uma tentativa
  // (exameEmCursoId definido), sair da aba/janela ANULA a tentativa —
  // ver aviso mostrado antes de começar o exame. Não dispara ao trocar
  // de aba fora de um exame nem quando volta a ficar visível (só na
  // saída, para não contar o mesmo evento 2x).
  //
  // Dispara dois pedidos em paralelo, de propósito: o normal (via
  // NgRx/HttpClient, cobre o caso comum de trocar de aba) e um `fetch`
  // com `keepalive: true` (sobrevive ao browser a fechar a aba/janela
  // no mesmo instante, o que cancelaria um pedido normal a meio) — o
  // back-end é seguro a receber os dois (o segundo é um no-op).
  @HostListener('document:visibilitychange')
  onVisibilidadeMudou() {
    const exame_id = this.exameEmCursoId();
    if (document.hidden && exame_id && this.educandoSelecionadoId) {
      const aluno_id = this.educandoSelecionadoId;
      this.store.dispatch(registarEventoSuspeito({ aluno_id, exame_id }));
      this.enviarSinalDeSaidaComKeepalive(`/api/v1/portal/educandos/${aluno_id}/exames/${exame_id}/evento-suspeito`);
    }
  }

  // Câmara/microfone obrigatório(a) parou de transmitir a meio do exame
  // (permissão revogada, dispositivo desligado).
  private onTrackObrigatoriaParou(tipo: 'camera' | 'microfone') {
    const exame_id = this.exameEmCursoId();
    if (!exame_id || !this.educandoSelecionadoId) return;
    const aluno_id = this.educandoSelecionadoId;
    this.store.dispatch(registarViolacaoDispositivo({ aluno_id, exame_id, tipo }));
    this.enviarSinalDeSaidaComKeepalive(`/api/v1/portal/educandos/${aluno_id}/exames/${exame_id}/violacao-dispositivo`, { tipo });
  }

  private enviarSinalDeSaidaComKeepalive(url: string, corpo: Record<string, unknown> = {}) {
    const token = localStorage.getItem('saas_access_token');
    if (!token) return;
    fetch(url, {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(corpo),
    }).catch(() => { /* melhor esforço — o pedido normal via NgRx já cobre o caso comum */ });
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

  // Fatura cujo campo "referência" de auto-relato está aberto — só um
  // de cada vez, mesmo padrão de templateEmEdicaoTipo em documentos.component.ts.
  faturaAReportarId: string | null = null;
  referenciaPagamentoReportado = '';

  onAlternarReportarPagamento(faturaId: string) {
    this.faturaAReportarId = this.faturaAReportarId === faturaId ? null : faturaId;
    this.referenciaPagamentoReportado = '';
  }

  onConfirmarReportarPagamento(faturaId: string, contratoId: string) {
    this.store.dispatch(reportarPagamentoFatura({
      fatura_id: faturaId, contrato_id: contratoId, referencia: this.referenciaPagamentoReportado.trim() || null
    }));
    this.faturaAReportarId = null;
    // reportarPagamentoFatura$ só atualiza store/financeiro — mesmo
    // motivo/padrão de onPagarComPayPal e capturarPagamento acima.
    this.actions$.pipe(ofType(financeiroOperacaoSucesso), take(1)).subscribe(() => {
      if (this.educandoSelecionadoId) {
        this.store.dispatch(carregarFinanceiroDoEducando({ aluno_id: this.educandoSelecionadoId }));
      }
    });
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

  // --- Comunicados ---
  onVerAnexoComunicado(comunicadoId: string) {
    if (!this.educandoSelecionadoId) return;
    const aba = window.open('', '_blank');
    this.http.get(`/api/v1/portal/educandos/${this.educandoSelecionadoId}/comunicados/${comunicadoId}/anexo`, { responseType: 'blob' }).subscribe({
      next: (blob) => abrirOuTransferirBlob(aba, blob, 'anexo'),
      error: () => { if (aba) aba.close(); }
    });
  }

  onAbrirRespostaComunicado(comunicadoId: string) {
    this.respostaComunicadoAberta = comunicadoId;
    this.textoRespostaComunicado = '';
  }

  onEnviarRespostaComunicado(comunicadoId: string) {
    if (!this.textoRespostaComunicado.trim() || !this.educandoSelecionadoId) return;
    // Só interessa a PRÓXIMA resposta enviada (take(1)) — mesmo idioma
    // já usado em comunicacoes.component.ts para o fluxo de anexo.
    this.actions$.pipe(ofType(responderComunicadoSucesso), take(1)).subscribe(() => {
      this.comunicadosRespondidos.update(atuais => new Set(atuais).add(comunicadoId));
    });
    this.store.dispatch(responderComunicado({
      aluno_id: this.educandoSelecionadoId, comunicado_id: comunicadoId, corpo: this.textoRespostaComunicado
    }));
    this.respostaComunicadoAberta = null; // fecha já — confirmação otimista
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
