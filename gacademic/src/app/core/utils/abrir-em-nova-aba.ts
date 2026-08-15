/**
 * Padrão usado em toda a app para abrir conteúdo que exige o cabeçalho
 * Authorization (PDFs de documentos, aprovação PayPal): a aba de
 * destino é pré-aberta em branco de forma SÍNCRONA dentro do próprio
 * handler de clique (`window.open('', '_blank')`), porque é isso que
 * evita o bloqueio de pop-up — só depois é que se sabe o conteúdo
 * final (o blob do PDF, ou a approve_url do PayPal), altura em que já
 * é tarde para abrir uma aba nova sem ser bloqueado.
 *
 * Mas `window.open('', '_blank')` pode DEVOLVER null mesmo dentro de
 * um gesto de clique genuíno — depende do browser, de extensões
 * (bloqueadores de anúncios/pop-ups) e das permissões que o
 * utilizador já deu ao site. Quando isso acontece, o código anterior
 * limitava-se a não fazer nada (`if (aba) ...`), e o utilizador via o
 * botão "funcionar" (o pedido ao back-end tinha sucesso) sem
 * absolutamente nada acontecer — o bug reportado em "Ver PDF".
 *
 * Estas funções tratam esse caso: se a aba pré-aberta não estiver
 * disponível, caem para uma alternativa que quase nunca é bloqueada.
 */

/** Blob (ex.: PDF) — cai para download forçado via <a> sintético, que não é bloqueado por pop-up blockers (não abre janela nova). */
export function abrirOuTransferirBlob(aba: Window | null, blob: Blob, nomeFicheiro: string): void {
  const url = URL.createObjectURL(blob);
  if (aba && !aba.closed) {
    aba.location.href = url;
    return;
  }
  const link = document.createElement('a');
  link.href = url;
  link.download = nomeFicheiro;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  // Não revoga o object URL de imediato — o próprio <a download> ainda
  // precisa dele para iniciar a transferência; o browser liberta-o
  // sozinho quando a aba/documento for descartado.
}

/** URL absoluta (ex.: approve_url do PayPal) — cai para navegação na própria aba em vez de silenciosamente não fazer nada. */
export function abrirOuNavegar(aba: Window | null, url: string): void {
  if (aba && !aba.closed) {
    aba.location.href = url;
    return;
  }
  window.location.href = url;
}
