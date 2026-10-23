const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch({args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
const p=await b.newPage({viewport:{width:1920,height:1080}}); const errs=[]; p.on('pageerror',e=>errs.push(e.message)); p.on('console',m=>{if(m.type()==='error')errs.push(m.text())});
await p.goto('file:///root/starcoach-hack/presentation/index.html#1'); await p.waitForTimeout(1500);
const n=await p.evaluate(()=>document.querySelectorAll('.slide').length);
for(let i=1;i<=n;i++){ await p.evaluate(i=>{location.hash=i;},i); await p.keyboard.press('Home'); for(let k=1;k<i;k++) await p.keyboard.press('ArrowLeft'); await p.waitForTimeout(i===14?4200:3600); await p.screenshot({path:`../assets/deck/s${String(i).padStart(2,'0')}.png`}); }
console.log('slides',n,'errors',errs); await b.close();})();
