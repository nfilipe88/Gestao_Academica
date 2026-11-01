// Abre a receita de produção num Chrome real e confirma o que o curl não vê:
// a CSP não parte a página. Nasceu de um bug real: a CSP bloqueava o
// onload="this.media='all'" gerado pelo Angular e o site inteiro abria sem
// CSS, com o curl a dizer 200 em tudo.
//
//   node ensaio-local/verificar-browser.mjs [https://localhost]
//
// Sem dependências (Node 22+: fetch e WebSocket nativos). O Chrome vem de
// CHROME_BIN ou dos sítios habituais; perfil temporário, apagado no fim.
// Sai com código 1 se alguma verificação falhar.
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const BASE = process.argv[2] ?? 'https://localhost';
const PORTA = 9333;
const PAGINAS = ['/', '/login', '/precos', '/privacidade', '/registo'];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const chromeBin = process.env.CHROME_BIN ?? [
  '/usr/bin/google-chrome',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
].find(existsSync) ?? 'google-chrome';

const perfil = mkdtempSync(join(tmpdir(), 'ensaio-chrome-'));
const chrome = spawn(chromeBin, [
  '--headless=new', '--ignore-certificate-errors', `--remote-debugging-port=${PORTA}`,
  `--user-data-dir=${perfil}`, '--no-first-run', '--disable-extensions',
  ...(process.env.CI ? ['--no-sandbox'] : []),
  'about:blank',
], { stdio: 'ignore' });

let id = 0;
const pendentes = new Map();
let ws;
const cmd = (method, params = {}) => new Promise((resolve) => {
  const n = ++id;
  pendentes.set(n, resolve);
  ws.send(JSON.stringify({ id: n, method, params }));
});
const avaliar = async (expressao) =>
  (await cmd('Runtime.evaluate', { expression: expressao, returnByValue: true, awaitPromise: true })).result?.result?.value;

async function ligar() {
  for (let i = 0; i < 60; i++) {
    try {
      const alvos = await (await fetch(`http://127.0.0.1:${PORTA}/json/list`)).json();
      const pagina = alvos.find((a) => a.type === 'page');
      if (pagina) return pagina.webSocketDebuggerUrl;
    } catch { /* ainda a arrancar */ }
    await sleep(500);
  }
  throw new Error('O Chrome não respondeu.');
}

const falhas = [];
function verificar(pagina, nome, ok, detalhe = '') {
  console.log(`  [${ok ? 'OK' : 'FALHA'}] ${nome}${detalhe ? ` — ${detalhe}` : ''}`);
  if (!ok) falhas.push(`${pagina}: ${nome}${detalhe ? ` — ${detalhe}` : ''}`);
}

try {
  ws = new WebSocket(await ligar());
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let csp = [];
  let excecoes = [];
  ws.onmessage = ({ data }) => {
    const m = JSON.parse(data);
    if (m.id && pendentes.has(m.id)) { pendentes.get(m.id)(m); pendentes.delete(m.id); return; }
    if (m.method === 'Log.entryAdded' && /Content.Security.Policy/i.test(m.params.entry.text ?? '')) csp.push(m.params.entry.text.slice(0, 160));
    if (m.method === 'Runtime.exceptionThrown') excecoes.push((m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text).slice(0, 160));
  };
  for (const dominio of ['Log', 'Runtime', 'Page']) await cmd(`${dominio}.enable`);

  for (const pagina of PAGINAS) {
    console.log(`\n${pagina}`);
    csp = []; excecoes = [];
    await cmd('Page.navigate', { url: BASE + pagina });
    await sleep(4000);
    verificar(pagina, 'Sem violações de CSP', csp.length === 0, [...new Set(csp)][0] ?? '');
    verificar(pagina, 'Sem exceções de JavaScript', excecoes.length === 0, excecoes[0] ?? '');
    verificar(pagina, 'O Angular arrancou', Boolean(await avaliar(`document.querySelector('[ng-version]')?.getAttribute('ng-version')`)));
    // A folha principal tem de estar carregada e ativa no ecrã. Só CSS crítico
    // embebido não chega: era esse o sintoma do bug, com a página toda partida.
    const folhas = await avaliar(`[...document.styleSheets].filter(s => s.href && /styles-/.test(s.href) && !/print/.test(s.media.mediaText)).length`);
    verificar(pagina, 'A folha de estilos principal está ativa', folhas > 0, `${folhas} ativa(s)`);
  }

  // Os erros do front-end têm de conseguir chegar ao Sentry (SENTRY_DSN_FRONTEND).
  console.log('\nLigações externas');
  csp = [];
  await avaliar(`fetch('https://o1.ingest.sentry.io/api/1/envelope/', { method: 'POST', mode: 'no-cors' }).catch(() => null).then(() => 1)`);
  await sleep(500);
  verificar('sentry', 'A CSP deixa enviar erros ao Sentry', csp.length === 0, csp[0] ?? '');

  const saude = await avaliar(`fetch('/api/v1/health').then(r => r.status)`);
  verificar('api', 'A API responde através do nginx', saude === 200, String(saude));
} catch (erro) {
  falhas.push(String(erro));
} finally {
  chrome.kill();
  await sleep(500);
  try { rmSync(perfil, { recursive: true, force: true }); } catch { /* o Chrome ainda pode estar a fechar */ }
}

if (falhas.length) {
  console.error(`\n${falhas.length} verificação(ões) falharam:\n- ${[...new Set(falhas)].join('\n- ')}`);
  process.exit(1);
}
console.log('\nTudo certo no browser real.');
process.exit(0);
