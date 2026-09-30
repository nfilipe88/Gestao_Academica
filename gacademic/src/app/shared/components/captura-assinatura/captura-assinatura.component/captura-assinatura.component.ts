import { afterNextRender, Component, ElementRef, EventEmitter, inject, Injector, Input, Output, ViewChild } from '@angular/core';
import SignaturePad from 'signature_pad';

// Componente partilhado de captura de assinatura — usado tanto em
// Configurações (assinatura oficial da escola) como em Perfil
// (assinatura pessoal). Dois modos: carregar uma imagem já existente,
// ou desenhar ao vivo num <canvas> — funciona em qualquer ecrã tátil,
// incluindo ao aceder à plataforma pelo telemóvel (signature_pad trata
// rato e toque da mesma forma, sem código nenhum extra aqui).
//
// Emite sempre um File pronto a meter num FormData — o desenho é
// convertido para PNG (toDataURL -> Blob) antes de emitir, para o
// consumidor nunca ter de saber a diferença entre os dois modos.
@Component({
  selector: 'app-captura-assinatura',
  imports: [],
  templateUrl: './captura-assinatura.component.html',
  styleUrl: './captura-assinatura.component.css',
})
export class CapturaAssinaturaComponent {
  @Input() aEnviar = false;
  @Output() ficheiroPronto = new EventEmitter<File>();

  @ViewChild('canvasAssinatura') private canvasRef?: ElementRef<HTMLCanvasElement>;
  private injector = inject(Injector);

  modo: 'upload' | 'desenhar' = 'upload';
  canvasTemTraco = false;
  private signaturePad: SignaturePad | null = null;

  onEscolherDesenhar() {
    this.modo = 'desenhar';
    this.canvasTemTraco = false;
    // O <canvas> só entra no DOM depois de `modo` mudar (ver template,
    // @if) — em modo zoneless a deteção de alterações não é síncrona,
    // por isso um queueMicrotask() aqui corria ANTES de Angular ter
    // sequer agendado o re-render (bug real, apanhado só ao testar ao
    // vivo: o SignaturePad nunca chegava a ser criado). afterNextRender
    // é o mecanismo correto do Angular para isto — garante que só
    // corre depois do próximo ciclo de render ter mesmo acontecido.
    afterNextRender(() => this._iniciarCanvas(), { injector: this.injector });
  }

  onEscolherUpload() {
    this.modo = 'upload';
    this.signaturePad?.off();
    this.signaturePad = null;
  }

  private _iniciarCanvas() {
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas) return;
    // Canvas nítido em ecrãs de alta densidade (telemóvel) — sem isto,
    // o traço fica visivelmente pixelado nesses dispositivos.
    const proporcao = window.devicePixelRatio || 1;
    canvas.width = canvas.offsetWidth * proporcao;
    canvas.height = canvas.offsetHeight * proporcao;
    canvas.getContext('2d')?.scale(proporcao, proporcao);

    this.signaturePad = new SignaturePad(canvas, { backgroundColor: 'rgba(255,255,255,0)' });
    this.signaturePad.addEventListener('endStroke', () => {
      this.canvasTemTraco = !this.signaturePad!.isEmpty();
    });
  }

  onLimparCanvas() {
    this.signaturePad?.clear();
    this.canvasTemTraco = false;
  }

  onSelecionarFicheiro(evento: Event) {
    const ficheiro = (evento.target as HTMLInputElement).files?.[0];
    (evento.target as HTMLInputElement).value = ''; // permite voltar a escolher o mesmo ficheiro depois
    if (ficheiro) this.ficheiroPronto.emit(ficheiro);
  }

  async onUsarDesenho() {
    if (!this.signaturePad || this.signaturePad.isEmpty()) return;
    const resposta = await fetch(this.signaturePad.toDataURL('image/png'));
    const blob = await resposta.blob();
    this.ficheiroPronto.emit(new File([blob], 'assinatura.png', { type: 'image/png' }));
  }
}
