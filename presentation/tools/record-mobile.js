// Records the real product journey (web app + live backend) as a video, and grabs key screenshots.
const { chromium } = require('playwright');
const fs = require('fs');
const OUT = process.argv[2] || '../assets';
const BASE = 'http://127.0.0.1:3000/', API = 'http://127.0.0.1:8080/api';
fs.mkdirSync(OUT + '/shots', { recursive: true });
let T0 = Date.now(); const marks = {}; const mark = (k) => { marks[k] = +((Date.now() - T0) / 1000).toFixed(2); };

const RING_CSS = `
#ph{position:fixed;left:28px;bottom:24px;z-index:2147483000;width:230px;font-family:Vazirmatn,system-ui,sans-serif;direction:rtl;transform:translateY(140%);transition:transform .6s cubic-bezier(.2,.9,.3,1)}
#ph.show{transform:none}
#ph .fr{border-radius:34px;padding:9px;background:#111;box-shadow:0 24px 60px rgba(0,0,0,.45),0 0 0 2px #333;position:relative}
#ph img{display:block;width:100%;border-radius:26px}
#ph.ring .fr{animation:shake .5s infinite}
@keyframes shake{0%,100%{transform:rotate(0)}15%{transform:rotate(-3deg) translateX(-3px)}30%{transform:rotate(3deg) translateX(3px)}45%{transform:rotate(-2deg)}60%{transform:rotate(2deg)}}
#ph .wave{position:absolute;inset:-6px;border-radius:40px;border:3px solid #ef4056;opacity:0;animation:wv 1.2s infinite}
#ph.ring .wave{opacity:1}
#ph .wave.w2{animation-delay:.4s}
@keyframes wv{0%{transform:scale(1);opacity:.9}100%{transform:scale(1.18);opacity:0}}
#ph .cap{margin-top:10px;text-align:center;background:#ef4056;color:#fff;font-weight:700;font-size:14px;padding:7px 10px;border-radius:12px;box-shadow:0 8px 24px rgba(239,64,86,.4)}
#ph .cap.ok{background:#16a34a;box-shadow:0 8px 24px rgba(22,163,74,.4)}
`;
async function phone(p, img64, cap, ring, ok) {
  await p.evaluate(([css, img, cap, ring, ok]) => {
    let st = document.getElementById('phst'); if (!st) { st = document.createElement('style'); st.id = 'phst'; st.textContent = css; document.head.appendChild(st); }
    let el = document.getElementById('ph');
    if (!el) { el = document.createElement('div'); el.id = 'ph'; el.innerHTML = '<div class="fr"><i class="wave"></i><i class="wave w2"></i><img alt=""></div><div class="cap"></div>'; document.body.appendChild(el); void el.offsetWidth; }
    el.querySelector('img').src = 'data:image/png;base64,' + img; const c = el.querySelector('.cap'); c.textContent = cap; c.className = 'cap' + (ok ? ' ok' : '');
    el.classList.toggle('ring', !!ring); requestAnimationFrame(() => el.classList.add('show'));
  }, [RING_CSS, img64, cap, ring, ok]);
}
const hidePhone = (p) => p.evaluate(() => { const e = document.getElementById('ph'); e && e.classList.remove('show'); });
const IMG = (f) => fs.readFileSync(__dirname + '/../../merchentappimages/named/' + f).toString('base64');

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const CURSOR = `
(() => { if (window.__cur) return; const c = document.createElement('div'); window.__cur = c;
 c.style.cssText='position:fixed;z-index:2147483647;width:30px;height:30px;border-radius:50%;background:rgba(240,60,90,.35);border:2px solid #f03c5a;pointer-events:none;transform:translate(-50%,-50%);transition:transform .08s;left:-50px;top:-50px;box-shadow:0 0 0 6px rgba(240,60,90,.12)';
 document.documentElement.appendChild(c);
 addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
 addEventListener('mousedown', () => { c.style.transform='translate(-50%,-50%) scale(.6)'; }, true);
 addEventListener('mouseup', () => { c.style.transform='translate(-50%,-50%) scale(1)'; }, true);
})();`;

(async () => {
  const b = await chromium.launch({ args: ['--no-sandbox'] });
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, recordVideo: { dir: OUT + '/_vid', size: { width: 585, height: 1266 } } });
  const p = await ctx.newPage(); T0 = Date.now();
  await p.addInitScript(CURSOR);
  await p.addInitScript(() => { try { localStorage.setItem('nq-merchant-shop', 'shop_jimbo_test'); localStorage.removeItem('nq-inq-v1'); sessionStorage.clear(); } catch (e) {} });
  let n = 0; const shot = async (name) => { await p.screenshot({ path: `${OUT}/shots/${String(++n).padStart(2, '0')}_${name}.png` }); };
  const go = async (sel, opt = {}) => { const el = p.locator(sel).first(); await el.waitFor({ timeout: 8000 }); await el.scrollIntoViewIfNeeded(); await wait(opt.pause ?? 500); const bb = await el.boundingBox(); await p.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2, { steps: 14 }); await wait(250); await el.evaluate((e) => e.click()); await wait(opt.after ?? 900); };
  const type = async (sel, text) => { await p.locator(sel).first().click(); await p.keyboard.type(text, { delay: 55 }); };
  const safe = async (name, fn) => { try { await fn(); } catch (e) { console.log('STEP FAILED', name, e.message.split('\n')[0]); } };

  await p.goto(BASE + '#agent'); await wait(1800);
  await shot('home_agent');

  // ---- Scene 1: TorobChat (backend AI over the real catalogue) ----
  await safe('chat', async () => {
    await type('#agInput', 'یه گوشی سامسونگ میخوام'); await wait(500); await shot('chat_typed');
    await go('#agSend', { after: 300 });
    await p.locator('#agLog .ag-chip').first().waitFor({ timeout: 25000 }); await wait(900); await shot('chat_clarify');
    for (let i = 0; i < 3 && !(await p.locator('.bk-card').count()); i++) {
      await go('#agLog .ag-msg.bot:last-child .ag-chip >> nth=1', { after: 300 });
      await Promise.race([p.locator('.bk-card').first().waitFor({ timeout: 25000 }), p.locator('#agLog .ag-msg.bot:last-child .ag-chip').first().waitFor({ timeout: 25000 })]).catch(() => {});
      await wait(900);
    }
    await shot('chat_results');
    await p.evaluate(() => { const l = document.querySelector('#agLog'); l && l.scrollTo({ top: l.scrollHeight, behavior: 'smooth' }); }); await wait(1800); await shot('chat_results_bottom');
  });

  // ---- Scene 2: List -> product -> stores ----
  await safe('list', async () => {
    await p.goto('about:blank'); await p.goto(BASE + '#list'); await wait(1600);
    await p.locator('#q').click(); await wait(300); await p.keyboard.type('هدفون', { delay: 140 }); await wait(1200); await shot('list_products');
    await p.locator('#q').blur(); await wait(500);
    await go('#prods .prod-main >> nth=1', { after: 1600 }); await shot('list_stores');
  });

  // ---- Scene 3: Map ----
  await safe('map', async () => {
    await go('.view-tab[data-view="map"]', { after: 2500 }); await shot('map');
    await go('.view-tab[data-view="list"]', { after: 700 });
  });

  // ---- Scene 4: store dialog -> inquiry ----
  let remote = null;
  await safe('inquiry', async () => {
    await go('#cards .card-main >> nth=0', { after: 1200 }); await shot('store_card_open');
    await p.evaluate(() => { const d = document.querySelector('#storeDlg'); if (d && !d.open) {} });
    await go('[data-inq]', { after: 1000 }); await shot('inquiry_dialog');
    await go('[data-inq-torob]', { after: 1500 }); mark('sent'); await shot('inquiry_sent');
    await go('.view-tab[data-view="inq"]', { after: 1500 }); await shot('inquiries_pending');
    mark('ring');
    await wait(2500); await shot('merchant_ring_moment');
    remote = await p.evaluate(() => { const q = NQ.Inq.list().find((x) => x.remote); return q && q.remote; });
  });

  // ---- Scene 5: merchant answers (same API the Android app calls) ----
  if (remote) {
    const hdr = { 'Content-Type': 'application/json' };
    await fetch(API + '/seller/auth/request-otp', { method: 'POST', headers: hdr, body: JSON.stringify({ phone_number: '09120000000' }) });
    const tok = (await (await fetch(API + '/seller/auth/verify-otp', { method: 'POST', headers: hdr, body: JSON.stringify({ phone_number: '09120000000', otp_code: '123456' }) })).json()).access_token;
    await wait(2500);
    await fetch(API + `/seller/inquiries/${remote}/respond`, { method: 'POST', headers: { ...hdr, Authorization: 'Bearer ' + tok }, body: JSON.stringify({ client_response_id: 'rec-' + Date.now(), offered_price_toman: 1380000, is_in_stock: true, stock_count: 4, notes: 'موجود است؛ تا ساعت ۲۱ در فروشگاه هستیم و برای شما نگه می‌داریم.', submitted_at: new Date().toISOString() }) });
    await p.waitForFunction(() => NQ.Inq.list().some((q) => q.remote && q.status === 'answered'), null, { timeout: 15000 }).catch(() => {}); mark('answered'); await wait(1800); await shot('inquiry_answered'); await wait(2500);
  }
  await ctx.close(); await b.close();
  const vids = fs.readdirSync(OUT + '/_vid'); fs.renameSync(`${OUT}/_vid/${vids[0]}`, `${OUT}/app-demo.webm`); fs.rmdirSync(OUT + '/_vid');
  fs.writeFileSync(OUT + '/timeline.json', JSON.stringify(marks)); console.log('done', remote, marks);
})();
