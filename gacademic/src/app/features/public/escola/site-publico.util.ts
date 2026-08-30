/** Link wa.me a partir do número guardado (só dígitos) — com uma
 * mensagem inicial já preenchida, para poupar um passo a quem clica.
 * Partilhado por todos os modelos (./templates/*). */
export function linkWhatsapp(whatsapp: string, nomeEscola: string): string {
  const mensagem = encodeURIComponent(`Olá! Vi a página de ${nomeEscola} e gostava de saber mais.`);
  return `https://wa.me/${whatsapp}?text=${mensagem}`;
}
