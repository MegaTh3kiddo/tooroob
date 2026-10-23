const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch({args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
const p=await b.newPage({viewport:{width:1920,height:1080}});
await p.goto('file:///root/starcoach-hack/presentation/index.html#11'); await p.waitForTimeout(2500);
for(const t of [3,44.5,47.5,50]){ await p.evaluate(t=>{const v=document.getElementById('demoVid');v.currentTime=t;},t); await p.waitForTimeout(1500); await p.screenshot({path:`../assets/deck/v_${t}.png`}); }
console.log(await p.evaluate(()=>{const v=document.getElementById('demoVid');return [v.currentSrc.split('/').pop(),v.videoWidth,v.duration]}));
await b.close();})();
