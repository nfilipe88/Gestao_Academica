import { AsyncPipe, CurrencyPipe, DatePipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Store } from '@ngrx/store';
import { Actions, ofType } from '@ngrx/effects';
import { take } from 'rxjs';
import { selectPerfilAcesso } from '../../../store/auth/auth.selectors';
import { carregarAlunos, carregarResponsaveis } from '../../../store/alunos/alunos.actions';
import { selectAlunos, selectResponsaveis } from '../../../store/alunos/alunos.selector';
import { carregarProfessores } from '../../../store/professores/professores.actions';
import { selectProfessores } from '../../../store/professores/professores.selector';
import * as DocumentosActions from '../../../store/documentos/documentos.actions';
import {
  selectDocumentosError, selectDocumentosMensagem, selectMinhasSolicitacoesEscola,
  selectPaginacaoSolicitacoesEmissao, selectPaginacaoSolicitacoesEscolaStaff, selectPrecosDocumento,
  selectSolicitacoesEmissao, selectSolicitacoesEscolaStaff, selectTemplatesDocumento
} from '../../../store/documentos/documentos.selector';
import { DestinatarioEscola, TemplateDocumento, VARIAVEIS_TEMPLATE } from '../../../store/documentos/documentos.models';
import { selectMoeda } from '../../../store/configuracoes/configuracoes.selector';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';

type Aba = 'emissao' | 'precos' | 'modelos' | 'pedidos-escola' | 'minhas-respostas';

@Component({
  selector: 'app-documentos.component',
  imports: [AsyncPipe, CurrencyPipe, DatePipe, FormsModule, PaginacaoComponent],
  templateUrl: './documentos.component.html',
  styleUrl: './documentos.component.css',
})
export class DocumentosComponent implements OnInit {
  private store = inject(Store);
  private http = inject(HttpClient);
  private actions$ = inject(Actions);

  perfil$ = this.store.select(selectPerfilAcesso);
  precos$ = this.store.select(selectPrecosDocumento);
  templates$ = this.store.select(selectTemplatesDocumento);
  readonly variaveisTemplate = VARIAVEIS_TEMPLATE;
  solicitacoesEmissao$ = this.store.select(selectSolicitacoesEmissao);
  paginacaoSolicitacoesEmissao$ = this.store.select(selectPaginacaoSolicitacoesEmissao);
  solicitacoesEscolaStaff$ = this.store.select(selectSolicitacoesEscolaStaff);
  paginacaoSolicitacoesEscolaStaff$ = this.store.select(selectPaginacaoSolicitacoesEscolaStaff);
  minhasSolicitacoesEscola$ = this.store.select(selectMinhasSolicitacoesEscola);
  alunos$ = this.store.select(selectAlunos);
  professores$ = this.store.select(selectProfessores);
  responsaveis$ = this.store.select(selectResponsaveis);
  mensagem$ = this.store.select(selectDocumentosMensagem);
  erro$ = this.store.select(selectDocumentosError);
  moeda$ = this.store.select(selectMoeda);

  aba: Aba = 'emissao';

  // Formulário "Novo pedido à escola"
  mostrarFormularioPedido = false;
  novoPedidoTipo: DestinatarioEscola = 'ALUNO';
  novoPedidoDestinatarioId = '';
  novoPedidoTitulo = '';
  novoPedidoDescricao = '';

  // Entrega física: id da solicitação com o formulário de observações aberto
  solicitacaoAEntregar: string | null = null;
  observacoesEntrega = '';

  // Resposta a pedido da escola (aba "minhas-respostas")
  respostaAberta: string | null = null;
  textoResposta = '';

  souGestorOuSecretaria = false;

  paginaEmissao = 1;
  tamanhoEmissao = 25;
  paginaEscola = 1;
  tamanhoEscola = 25;

  ngOnInit() {
    // GESTOR/SECRETARIA gerem pedidos de emissão e pedidos-à-escola
    // (exigir_perfil no back-end); um PROFESSOR só vê "Pedidos que me
    // fizeram" — despachar os endpoints staff-only para ele daria 403.
    this.perfil$.pipe(take(1)).subscribe(perfil => {
      this.souGestorOuSecretaria = perfil === 'GESTOR' || perfil === 'SECRETARIA';
      if (this.souGestorOuSecretaria) {
        this.store.dispatch(DocumentosActions.carregarSolicitacoesEmissaoStaff({ page: this.paginaEmissao, page_size: this.tamanhoEmissao }));
        this.store.dispatch(DocumentosActions.carregarSolicitacoesEscolaStaff({ page: this.paginaEscola, page_size: this.tamanhoEscola }));
        // page_size no máximo: povoam <select>, ver nota em transferencias.component.ts
        this.store.dispatch(carregarAlunos({ page_size: 100 }));
        this.store.dispatch(carregarProfessores({ page_size: 100 }));
        this.store.dispatch(carregarResponsaveis({ page_size: 100 }));
      } else {
        // Professor: começa direto na aba que lhe interessa.
        this.aba = 'minhas-respostas';
      }
    });
    this.store.dispatch(DocumentosActions.carregarMinhasSolicitacoesEscola());
  }

  onPaginaEmissao(pagina: number) {
    this.paginaEmissao = pagina;
    this.store.dispatch(DocumentosActions.carregarSolicitacoesEmissaoStaff({ page: pagina, page_size: this.tamanhoEmissao }));
  }

  onTamanhoEmissao(tamanho: number) {
    this.tamanhoEmissao = tamanho;
    this.paginaEmissao = 1;
    this.store.dispatch(DocumentosActions.carregarSolicitacoesEmissaoStaff({ page: 1, page_size: tamanho }));
  }

  onPaginaEscola(pagina: number) {
    this.paginaEscola = pagina;
    this.store.dispatch(DocumentosActions.carregarSolicitacoesEscolaStaff({ page: pagina, page_size: this.tamanhoEscola }));
  }

  onTamanhoEscola(tamanho: number) {
    this.tamanhoEscola = tamanho;
    this.paginaEscola = 1;
    this.store.dispatch(DocumentosActions.carregarSolicitacoesEscolaStaff({ page: 1, page_size: tamanho }));
  }

  irParaAba(aba: Aba) {
    this.aba = aba;
    if (aba === 'precos') {
      this.store.dispatch(DocumentosActions.carregarPrecos());
    } else if (aba === 'modelos') {
      this.store.dispatch(DocumentosActions.carregarTemplates());
    }
  }

  // --- Preços ---
  onGuardarPreco(tipo_documento: string, preco: number, ativo: boolean) {
    this.store.dispatch(DocumentosActions.atualizarPreco({ tipo_documento, preco, ativo }));
  }

  // --- Modelos de documentos (layout próprio por escola) ---
  // Só um editor aberto de cada vez (mesmo padrão de solicitacaoAEntregar/respostaAberta acima).
  templateEmEdicaoTipo: string | null = null;
  corpoEmEdicao = '';
  erroPreVisualizacao: string | null = null;

  // Strings simples interpoladas em vez de {{ }} literais escritos
  // diretamente no template: Angular decodifica entidades HTML como
  // &#123;&#123; para "{{" ANTES de procurar bindings, por isso
  // escrever "&#123;&#123; aluno_nome &#125;&#125;" no HTML era
  // interpretado como um binding real a uma propriedade
  // "aluno_nome" (que não existe) — daqui vinha o TS2339 no build.
  // Uma propriedade de string normal não sofre esse problema: o valor
  // interpolado nunca é reanalisado por bindings.
  readonly exemploSintaxeVariavel = '{{ nome_da_variavel }}';
  readonly exemploPlaceholderTemplate = '<p>Certifico que {{ aluno_nome }} estuda na turma {{ turma_nome }} no ano {{ ano_letivo }}.</p>';

  onIniciarEdicaoTemplate(template: TemplateDocumento) {
    this.templateEmEdicaoTipo = template.tipo_documento;
    this.corpoEmEdicao = template.corpo_html ?? '';
    this.erroPreVisualizacao = null;
  }

  onCancelarEdicaoTemplate() {
    this.templateEmEdicaoTipo = null;
    this.erroPreVisualizacao = null;
  }

  // Guardar pode falhar (template inválido/SSTI bloqueado pelo
  // sandbox, ver documentos_pdf.py) — fechar o editor de forma
  // otimista faria o Gestor perder o texto que escreveu mesmo quando
  // o erro aparece no banner do topo, sem ligação óbvia ao cartão que
  // estava a editar. Em vez disso, só fecha quando o efeito confirma
  // sucesso (templateAtualizado); em caso de falha o editor e o texto
  // ficam tal como estavam, para o Gestor corrigir e tentar de novo.
  onGuardarTemplate() {
    if (!this.templateEmEdicaoTipo || !this.corpoEmEdicao.trim()) return;
    this.store.dispatch(DocumentosActions.guardarTemplate({ tipo_documento: this.templateEmEdicaoTipo, corpo_html: this.corpoEmEdicao }));
    this.actions$.pipe(
      ofType(DocumentosActions.templateAtualizado, DocumentosActions.documentosOperacaoFalhou),
      take(1)
    ).subscribe(action => {
      if (action.type === DocumentosActions.templateAtualizado.type) {
        this.templateEmEdicaoTipo = null;
      }
    });
  }

  onReporPadrao(tipo_documento: string) {
    this.store.dispatch(DocumentosActions.reporTemplatePadrao({ tipo_documento }));
    if (this.templateEmEdicaoTipo === tipo_documento) this.templateEmEdicaoTipo = null;
  }

  // Pré-visualiza o texto ainda por guardar (não o que já está no
  // store) — o Gestor quer ver o efeito do que está a escrever, antes
  // de decidir guardar. Mesmo truque de separador pré-aberto que
  // onVerPdf usa (evita bloqueio de pop-up); erro de validação vem
  // como Blob (responseType:'blob' aplica-se à resposta toda, mesmo a
  // de erro), por isso é preciso ler o texto do blob para extrair a
  // mensagem em vez de usar err.error.detail diretamente.
  onPreVisualizarTemplate() {
    if (!this.templateEmEdicaoTipo || !this.corpoEmEdicao.trim()) return;
    const tipo = this.templateEmEdicaoTipo;
    this.erroPreVisualizacao = null;
    const aba = window.open('', '_blank');
    this.http.post(`/api/v1/documentos/templates/${tipo}/pre-visualizar`, { corpo_html: this.corpoEmEdicao }, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        if (aba) aba.location.href = url;
      },
      error: (err: HttpErrorResponse) => {
        if (aba) aba.close();
        const corpoErro = err.error;
        if (corpoErro instanceof Blob) {
          corpoErro.text().then(texto => {
            try {
              this.erroPreVisualizacao = JSON.parse(texto).detail ?? 'Não foi possível pré-visualizar o modelo.';
            } catch {
              this.erroPreVisualizacao = 'Não foi possível pré-visualizar o modelo.';
            }
          });
        } else {
          this.erroPreVisualizacao = 'Não foi possível pré-visualizar o modelo.';
        }
      }
    });
  }

  // --- Pedidos de emissão (staff) ---
  onAbrirEntrega(solicitacaoId: string) {
    this.solicitacaoAEntregar = solicitacaoId;
    this.observacoesEntrega = '';
  }

  onConfirmarEntrega(solicitacaoId: string) {
    this.store.dispatch(DocumentosActions.entregarFisico({ solicitacao_id: solicitacaoId, observacoes: this.observacoesEntrega || undefined }));
    this.solicitacaoAEntregar = null;
  }

  onCancelarSolicitacaoEmissao(solicitacaoId: string) {
    this.store.dispatch(DocumentosActions.cancelarSolicitacaoEmissao({ solicitacao_id: solicitacaoId }));
  }

  // O PDF exige o cabeçalho Authorization (Bearer) — um <a href> normal
  // não o envia (é uma navegação de browser, não passa pelo
  // HttpClient/jwt.interceptor), por isso vai dar sempre 401. Em vez
  // disso, pedimos o PDF via HttpClient e abrimos o blob resultante
  // numa aba já aberta de forma síncrona no clique (evita o bloqueio de
  // pop-up, mesmo truque do fluxo PayPal).
  onVerPdf(solicitacaoId: string) {
    const aba = window.open('', '_blank');
    this.http.get(`/api/v1/documentos/solicitacoes/${solicitacaoId}/pdf`, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        if (aba) aba.location.href = url;
      },
      error: () => { if (aba) aba.close(); }
    });
  }

  // --- Pedidos à escola (criar/gerir) ---
  onMudarTipoDestinatario(tipo: DestinatarioEscola) {
    this.novoPedidoTipo = tipo;
    this.novoPedidoDestinatarioId = '';
  }

  onSubmitNovoPedido() {
    if (!this.novoPedidoDestinatarioId || !this.novoPedidoTitulo || !this.novoPedidoDescricao) return;
    this.store.dispatch(DocumentosActions.criarSolicitacaoEscola({
      destinatario_tipo: this.novoPedidoTipo, destinatario_id: this.novoPedidoDestinatarioId,
      titulo: this.novoPedidoTitulo, descricao: this.novoPedidoDescricao,
    }));
    this.mostrarFormularioPedido = false;
    this.novoPedidoDestinatarioId = '';
    this.novoPedidoTitulo = '';
    this.novoPedidoDescricao = '';
  }

  onConcluirPedidoEscola(solicitacaoId: string) {
    this.store.dispatch(DocumentosActions.concluirSolicitacaoEscola({ solicitacao_id: solicitacaoId }));
  }

  // --- Pedidos que a escola me fez (Professor) ---
  onAbrirResposta(solicitacaoId: string) {
    this.respostaAberta = solicitacaoId;
    this.textoResposta = '';
  }

  onEnviarResposta(solicitacaoId: string) {
    if (!this.textoResposta.trim()) return;
    this.store.dispatch(DocumentosActions.responderSolicitacaoEscola({ solicitacao_id: solicitacaoId, resposta_texto: this.textoResposta }));
    this.respostaAberta = null;
  }
}
