import { AsyncPipe, CurrencyPipe, DatePipe } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Store } from '@ngrx/store';
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
  selectSolicitacoesEmissao, selectSolicitacoesEscolaStaff
} from '../../../store/documentos/documentos.selector';
import { DestinatarioEscola } from '../../../store/documentos/documentos.models';
import { PaginacaoComponent } from '../../../shared/components/paginacao/paginacao.component/paginacao.component';

type Aba = 'emissao' | 'precos' | 'pedidos-escola' | 'minhas-respostas';

@Component({
  selector: 'app-documentos.component',
  imports: [AsyncPipe, CurrencyPipe, DatePipe, FormsModule, PaginacaoComponent],
  templateUrl: './documentos.component.html',
  styleUrl: './documentos.component.css',
})
export class DocumentosComponent implements OnInit {
  private store = inject(Store);
  private http = inject(HttpClient);

  perfil$ = this.store.select(selectPerfilAcesso);
  precos$ = this.store.select(selectPrecosDocumento);
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
    }
  }

  // --- Preços ---
  onGuardarPreco(tipo_documento: string, preco: number, ativo: boolean) {
    this.store.dispatch(DocumentosActions.atualizarPreco({ tipo_documento, preco, ativo }));
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
