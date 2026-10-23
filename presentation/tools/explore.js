const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch({args:['--no-sandbox']});
const p=await b.newPage({viewport:{width:1440,height:900}});
await p.goto('http://127.0.0.1:3000/#list'); await p.waitForTimeout(1500);
await p.click('#chips button >> nth=0'); await p.waitForTimeout(800);
await p.click('#prods .prod-main >> nth=1'); await p.waitForTimeout(1200); await p.screenshot({path:'x/2.png'});
console.log(await p.evaluate(()=>[...document.querySelectorAll('#cards > li')].slice(0,1).map(e=>e.outerHTML.slice(0,1500))));
await b.close();})();
