// mammoth só publica .d.ts para o entry-point principal ("mammoth",
// para Node.js — ver node_modules/mammoth/lib/index.d.ts), não para
// "mammoth/mammoth.browser" (o entry-point de browser, usado em
// documentos.component.ts porque o principal depende de `fs`).
declare module 'mammoth/mammoth.browser' {
  interface ConvertToHtmlResult {
    value: string;
    messages: Array<{ type: 'warning' | 'error'; message: string }>;
  }

  export function convertToHtml(input: { arrayBuffer: ArrayBuffer }): Promise<ConvertToHtmlResult>;
}
