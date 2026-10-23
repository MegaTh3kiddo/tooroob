/* ترب مپ — منطق برنامه (state، رندر فهرست و مقایسه، رویدادها)
   وابستگی‌ها: js/data.js و js/map.js (باید قبل از این فایل لود شوند) */
(function () {
  'use strict';
  var NQ = window.NQ, MapView = NQ.MapView;
  var STORES = NQ.STORES, CATS = NQ.CATS, OFFERS = NQ.OFFERS, COLORS = NQ.COLORS, STOCK = NQ.STOCK, Plan = NQ.Plan, Travel = NQ.Travel, IC = NQ.ICONS;

  document.documentElement.setAttribute('lang', 'fa');
  document.documentElement.setAttribute('dir', 'rtl');

  var $ = function(s){return document.querySelector(s)};
  var fa = function(n){return Number(n).toLocaleString('fa-IR')};
  /* قیمت‌های خیلی بلند (میلیاردی) کمی کوچک‌تر نوشته می‌شوند تا از کارت بیرون نزنند */
  var longP = function(n){return String(Math.round(n)).length>9 ? ' long' : ''};
  var fa1 = function(n){return Number(n).toLocaleString('fa-IR',{minimumFractionDigits:1,maximumFractionDigits:1})};
  var clamp = function(v,a,b){return Math.min(b,Math.max(a,v))};
  var esc = function(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})};
  var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- ابزارها ---------- */
  function norm(s){
    return String(s).replace(/ي/g,'ی').replace(/ك/g,'ک').replace(/[‌\s]/g,'')
      .replace(/[۰-۹]/g,function(d){return '۰۱۲۳۴۵۶۷۸۹'.indexOf(d)}).toLowerCase();
  }
  function findCat(v){
    var q = norm(v); if(!q) return null;
    var best = null, bs = 0;
    CATS.forEach(function(c){
      var s = 0;
      [c.name].concat(c.words).forEach(function(w){
        var n = norm(w);
        var t = n===q ? 3 : n.indexOf(q)>-1 ? 2 : (q.indexOf(n)>-1 && n.length>2) ? 1 : 0;
        if(t>s) s=t;
      });
      if(s>bs){bs=s;best=c}
    });
    return best;
  }
  /* فاصلهٔ جاده‌ای تقریبی = فاصلهٔ هوایی × ۱٫۳ (برای مسیر واقعی می‌شود از OSRM / Valhalla استفاده کرد) */
  function roadKm(a, b) { return NQ.geo.distanceKm(a, b) * 1.3; }
  /* «آیکون روش رفت‌وآمد + x دقیقه»؛ در حالت پیشنهادی بهترین روش برای همان فاصله */
  function etaHTML(km, sid){
    var id = Travel.resolve(km, sid);
    return '<span class="eta" title="'+Travel.label(id)+'">'+IC[id]+'<span>'+fa(Travel.minutes(id,km))+' دقیقه</span></span>';
  }
  function routeText(km, sid){ return fa1(km)+' کیلومتر <i class="rsep">·</i> '+etaHTML(km, sid); }
  /* در مقایسه به‌جای A و B «اولی» و «دومی» نوشته می‌شود */
  var SLOT = {A:'اولی', B:'دومی'};
  /* زمان آخرین بروزرسانی قیمت: «امروز ۰۷:۱۵»، «دیروز ۲۲:۴۰» یا تاریخ */
  function whenTxt(h){
    var d = new Date(Date.now()-h*3600e3), now = new Date(), t = hm(d.getHours()*60+d.getMinutes());
    var day0 = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    if(d.getTime()>=day0) return 'امروز '+t;
    if(d.getTime()>=day0-864e5) return 'دیروز '+t;
    return d.toLocaleDateString('fa-IR',{day:'numeric',month:'long'});
  }
  function updHTML(h){ return '<span class="upd" data-hint="آخرین بروزرسانی قیمت: '+ago(h)+'"><span>بروزرسانی '+whenTxt(h)+'</span>'+IC.clock+'</span>'; }
  function ago(h){return h<1 ? 'چند دقیقه پیش' : h<24 ? fa(Math.round(h))+' ساعت پیش' : fa(Math.round(h/24))+' روز پیش'}
  function lt(l){return '<b class="lt '+l.toLowerCase()+'">'+SLOT[l]+'</b>'}

  /* ---------- فیلترها ----------
     یک مجموعه فیلتر روی «پیشنهادهای فروشگاه‌ها» اعمال می‌شود؛ هم برای فهرست فروشگاه‌ها و هم برای
     فهرست محصولات (محصول وقتی نمایش داده می‌شود که حداقل یک فروشگاهِ سازگار با فیلترها داشته باشد). */
  function defFilters(){
    return {stock:{in:true,unsure:true,out:true}, pmin:null, pmax:null, colors:[], brands:[], maxMin:0, torobpay:false, installment:false, openNow:false,
            warranty:false, kalabarg:false, fast:false, guarantee:false, minRate:0, maxKm:0, area:null, near:null};
  }
  function isOpenNow(st){var d=new Date(), h=d.getHours()+d.getMinutes()/60; return h>=st.openH && h<st.closeH}
  /* وضعیت باز/بسته بودن فروشگاه در همین لحظه (k: open | soon | closed) */
  function storeStatus(st){
    var d = new Date(), m = d.getHours()*60+d.getMinutes(), o = st.openH*60, c = st.closeH*60;
    if(m<o) return {k:'closed', short:'بسته است', text:'بسته است · امروز ساعت '+hm(o)+' باز می‌شود'};
    if(m>=c) return {k:'closed', short:'بسته است', text:'بسته است · فردا ساعت '+hm(o)+' باز می‌شود'};
    if(c-m<=60) return {k:'soon', short:'به‌زودی بسته می‌شود', text:'باز است · '+fa(c-m)+' دقیقه تا بسته شدن'};
    return {k:'open', short:'باز است', text:'باز است · تا ساعت '+hm(c)};
  }
  function statusHTML(st, full){ var x = storeStatus(st); return '<span class="ostat '+x.k+'">'+(full?x.text:x.short)+'</span>'; }
  /* تلفن و لینک‌ها */
  function toTel(p){
    var d = String(p).replace(/[۰-۹]/g,function(x){return '۰۱۲۳۴۵۶۷۸۹'.indexOf(x)}).replace(/\D/g,'');
    return d.charAt(0)==='0' ? '+98'+d.slice(1) : '+'+d;
  }
  function isMobileNo(p){ return /^[0۰][9۹]/.test(String(p).trim()); }
  function waNumber(st){ return toTel(st.phones.filter(isMobileNo)[0] || st.phones[0]).replace('+',''); }
  var GMODE = {walk:'walking', bike:'bicycling', transit:'transit', car:'driving', moto:'two-wheeler'};
  function routeURL(st, mode){
    return 'https://www.google.com/maps/dir/?api=1&origin='+state.origin.lat+','+state.origin.lng+'&destination='+st.lat+','+st.lng+'&travelmode='+(GMODE[mode]||'driving');
  }

  /* ---------- state ---------- */
  var state = {cat: null, dir: null, product: null, info: false, planInfo: {}, sinfo: {}, inqSent: {}, payOpen: {}, scoreOpen: {}, gx: null, pmore: {}, ppd: {}, planCmp: false, pPicks: {A: null, B: null}, pCat: null, sort: 'smart', filters: defFilters(), compare: false, picks: {A: null, B: null}, selected: null,
               pinfo: {}, pcmp: [],   // pcmp: شناسهٔ محصولات در مقایسه (تا ۵ تا)
               origin: {lat: NQ.ORIGIN.lat, lng: NQ.ORIGIN.lng}};

  state.tab = 'results'; state.planSel = null;
  var view = 'agent';   // صفحهٔ فعلی: agent (تربچت، پیش‌فرض) · list (بدون نقشه) · map
  var lastSched = null;
  var you_hint = $('#hint'), cardsEl = $('#cards'), prodsEl = $('#prods'), pcmpEl = $('#pcmp'), pickBarEl = $('#pickBar'), cmpEl = $('#cmp'), scrollEl = $('#scroll'), qEl = $('#q');

  function catById(id){return CATS.filter(function(c){return c.id===id})[0]||null}
  function mk(r, cat){
    cat = cat || state.cat;
    var st = STORES[r[0]], cols = [].concat(r[2]||[]);   // یک فروشگاه ممکن است چند رنگ از یک محصول داشته باشد (کالای خوراکی: بدون رنگ)
    return {sid:r[0],cat:cat,title:r[1],brand:NQ.brandOf(cat,r[1]),color:cols[0],colors:cols,price:r[3],stock:r[4],hrs:r[5],extra:r[6]||null,warranty:r[6]||'',store:st,km:roadKm(state.origin,st),ad:isAd(r[0],cat)};
  }
  /* آگهی ترب: فروشگاهی که در این دسته آگهی داده است */
  function isAd(sid, cat){ return ((NQ.ADS||{})[cat||state.cat]||[]).indexOf(sid)>-1; }
  /* پیشنهاد یک فروشگاه در یک دستهٔ مشخص (برای مقایسه در برنامهٔ سر زدن) */
  function offerIn(cat, sid){
    var r = (OFFERS[cat]||[]).filter(function(x){return x[0]===sid})[0];
    return r ? mk(r, cat) : null;
  }
  /* دایره‌های رنگ + نام رنگ‌ها */
  function colorsHTML(cols){
    return '<span class="sws">'+cols.map(function(c){return '<i class="sw" style="background:'+COLORS[c]+'"></i>'}).join('')+'</span>'+cols.join('، ');
  }
  function offer(sid){
    var p = curProd();
    var r = (OFFERS[state.cat]||[]).filter(function(x){return x[0]===sid && (!p || x[1]===p.title)})[0];
    return r ? mk(r) : null;
  }
  /* بدون محصولِ انتخاب‌شده همهٔ پیشنهادهای دسته برمی‌گردد (برای جاگیری نقشه و مرحلهٔ انتخاب مدل) */
  function rawRows(){
    if(!state.cat) return [];
    var p = curProd();
    return OFFERS[state.cat].filter(function(r){return !p || r[1]===p.title}).map(function(r){return mk(r)});   // نه map(mk): اندیس آرایه به‌جای دسته می‌رفت
  }
  function passes(o){
    var f = state.filters;
    if(!f.stock[o.stock]) return false;
    if(f.pmin!=null && o.price<f.pmin) return false;
    if(f.pmax!=null && o.price>f.pmax) return false;
    if(f.colors.length && !o.colors.some(function(c){return f.colors.indexOf(c)>-1})) return false;
    if(f.brands.length && f.brands.indexOf(o.brand)<0) return false;
    if(f.torobpay && !o.store.torobpay) return false;
    if(f.installment && !o.store.installment) return false;
    if(f.openNow && !isOpenNow(o.store)) return false;
    if(f.maxMin && Travel.minutesFor(o.km,o.sid)>f.maxMin) return false;
    if(f.fast && !o.store.fast) return false;
    if(f.guarantee && !o.store.guarantee) return false;
    if(f.minRate && (o.store.rating||0)<f.minRate) return false;
    if(f.maxKm && o.km>f.maxKm) return false;
    if(f.area && !inArea(o.store, f.area)) return false;
    if(f.near && !inCircle(o.store, f.near)) return false;
    if(f.warranty && !(o.extra && o.extra.m)) return false;
    if(f.kalabarg && !(o.extra && o.extra.kb)) return false;
    return true;
  }
  function offerRows(){ return rawRows().filter(passes); }
  function inArea(p, a){ return p.lat<=a.n && p.lat>=a.s && p.lng<=a.e && p.lng>=a.w; }
  /* دسته‌های خوراکی (مثل برنج): به‌جای گارانتی، پوشش کالابرگ */
  function isFood(cat){ return !!(catById(cat||state.cat)||{}).food; }

  /* ---------- محصولات (مدل‌ها) ---------- */
  var PRODS = NQ.PRODUCTS || {};
  function prodsOf(cat){return PRODS[cat]||[]}
  function prodById(id){return prodsOf(state.cat).filter(function(p){return p.id===id})[0]||null}
  function prodByTitle(t){return prodsOf(state.cat).filter(function(p){return p.title===t})[0]||null}
  function curProd(){return state.product ? prodById(state.product) : null}
  /* none: هنوز دسته‌ای نیست · pick: مدل را انتخاب کنید · stores: فهرست فروشگاه‌های یک مدل */
  function stage(){
    if(!state.cat) return state.dir ? 'dir' : 'none';
    if(!prodsOf(state.cat).length) return 'stores';
    return curProd() ? 'stores' : 'pick';
  }
  function shortOf(t){return String(t).replace(/^\S+\s+/,'')}
  /* نام خیلی کوتاه برای روی نقشه: فقط مدل (کلمه‌های لاتین پشت هم)، وگرنه سه کلمهٔ اول */
  function modelOf(t){
    var w = shortOf(t).split(/\s+/), out = [];
    if(/[A-Za-z]/.test(w[0])) for(var i=0; i<w.length && /^[A-Za-z0-9.+\-]+$/.test(w[i]); i++) out.push(w[i]);
    else out = w.slice(0,3);
    return out.join(' ') || shortOf(t);
  }

  function meta(){
    var live = offerRows().filter(function(o){return o.stock!=='out'});
    var best=null, near=null, max=0;
    live.forEach(function(o){
      if(!best||o.price<best.price) best=o;
      if(!near||o.km<near.km) near=o;
      if(o.price>max) max=o.price;
    });
    return {best:best&&best.sid,near:near&&near.sid,min:best?best.price:0,max:max};
  }
  function visibleRows(){
    var rows = offerRows();
    var m = meta();
    var key = {
      price:function(o){return o.price},
      near:function(o){return o.km},
      /* پیشنهادی: آگهی‌های ترب اول؛ بعد ترکیب قیمت مناسب، امتیاز فروشگاه، ضمانت ترب، ترب‌پی، به‌روز بودن قیمت (و کمی فاصله) */
      smart:function(o){
        return (o.ad && o.stock!=='out' ? -100 : 0) + o.price/(m.min||1) + (1-(o.store.trust==null?.8:o.store.trust))*.35 - (o.store.guarantee?.15:0) - (o.store.torobpay?.1:0) +
          Math.min(o.hrs,168)/168*.25 + (o.stock==='unsure'?.12:0) + o.km*.03;
      }
    }[state.sort];
    rows.sort(function(a,b){return ((a.stock==='out')-(b.stock==='out')) || (key(a)-key(b))});
    return rows;
  }
  function slotOf(sid){return state.picks.A===sid?'A':state.picks.B===sid?'B':null}

  /* ---------- نقشه ---------- */
  function fitPoints(P) { quietMap(); MapView.fit(P); }
  function fitResults() {
    var st = stage();
    if (st === 'none') { fitPoints([state.origin].concat(Object.keys(STORES).map(function (k) { return STORES[k]; }))); return; }
    if (st === 'dir') { fitPoints(circlePts(state.dir.near).concat(dirRows().map(function (k) { return STORES[k]; }))); return; }
    var rows = offerRows(); if (!rows.length) rows = rawRows();
    fitPoints([state.origin].concat(rows.map(function (o) { return o.store; })).concat(circlePts(state.filters.near)));
  }
  function fitPlan() {
    var pts = [state.origin].concat(Plan.stops.map(function (s) { return STORES[s.sid]; }));
    if (pts.length < 2) fitResults(); else fitPoints(pts);
  }
  function fitCurrent() { if (state.tab === 'plan') fitPlan(); else fitResults(); }
  /* توست: آیکون بر اساس نوع، دکمهٔ بستن، نوار زمان (با hover/focus متوقف می‌شود)، بستن با Esc */
  var toastTimer = 0, toastLeave = 0;
  var TOAST_ICONS = {
    success: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    info: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 11v6M12 7.2v.1"/></svg>',
    warn: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4l9 16H3z"/><path d="M12 10v4.5M12 17.4v.1"/></svg>'
  };
  function hideToast() {
    var el = $('#toast');
    if (el.hidden) return;
    clearTimeout(toastTimer); clearTimeout(toastLeave);
    el.classList.add('leave');
    toastLeave = setTimeout(function () { el.hidden = true; el.classList.remove('run', 'leave'); }, 180);
  }
  function toast(msg, kind) {
    var el = $('#toast'); kind = TOAST_ICONS[kind] ? kind : 'info';
    clearTimeout(toastTimer); clearTimeout(toastLeave);
    $('#toastMsg').textContent = msg;
    $('#toastIc').innerHTML = TOAST_ICONS[kind];
    el.setAttribute('data-kind', kind);
    var ms = clamp(msg.length * 65, 3500, 9000);
    el.style.setProperty('--toast-ms', ms + 'ms');
    el.hidden = false; el.classList.remove('run', 'leave'); void el.offsetWidth; el.classList.add('run');
    // پشتیبان: اگر انیمیشن اجرا نشد، همچنان بسته می‌شود (مگر موس روی آن باشد)
    toastTimer = setTimeout(function chk() {
      if (el.hidden) return;
      if (el.matches(':hover') || el.contains(document.activeElement)) { toastTimer = setTimeout(chk, 500); return; }
      hideToast();
    }, ms + 1200);
  }
  document.querySelector('#toast .toast-bar').addEventListener('animationend', hideToast);
  $('#toastX').addEventListener('click', hideToast);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hideToast(); });

  /* ---------- رندر ---------- */
  function renderChips(){
    $('#chips').innerHTML = CATS.map(function(c){
      return '<button type="button" class="chip" data-cat="'+c.id+'" aria-pressed="'+(state.cat===c.id)+'">'+c.name+'</button>';
    }).join('');
  }
  function renderControls(){
    Array.prototype.forEach.call(document.querySelectorAll('#sort button'),function(b){
      b.setAttribute('aria-checked',String(b.getAttribute('data-sort')===state.sort));
    });
    $('#cmpToggle').setAttribute('aria-pressed',String(state.tab==='plan' ? state.planCmp : state.compare));
    var st = stage();
    $('#sort').hidden = st==='none' || st==='dir';
    $('#cmpToggle').hidden = state.tab==='plan' ? Plan.count()<2 : st!=='stores';
    $('#filterBtn').hidden = st==='none' || st==='dir' || state.tab==='plan';
    renderFilterUI();
  }
  function renderSummary(rows){
    var el = $('#summary'), c = catById(state.cat);
    if(stage()==='dir'){
      var nd = dirRows().length;
      el.innerHTML = '<b>'+fa(nd)+' فروشگاه</b>'+(state.dir.kind && state.dir.kind!=='all' ? ' '+KIND_NAME[state.dir.kind] : '')+(state.dir.label ? ' · '+esc(state.dir.label) : '')+' <button type="button" class="link-btn" data-act="cleardir">پاک کردن</button>';
      return;
    }
    if(!c){el.textContent='نام یک محصول را بنویسید یا از گزینه‌های بالا انتخاب کنید.';return}
    var filt = activeFilterCount() ? ' (با فیلتر)' : '';
    if(stage()==='pick'){
      var np = pickList().length;
      el.innerHTML = '<b>'+fa(np)+' محصول</b>'+filt+' برای «'+c.name+'» پیدا شد · یکی را انتخاب کنید تا فروشگاه‌ها را ببینید'+(np>1?'، یا با آیکون مقایسه دو محصول را کنار هم بگذارید.':'.');
      return;
    }
    var m = meta(), p = curProd();
    var n = offerRows().length, tot = rawRows().length;
    el.innerHTML = '<b>'+fa(n)+' فروشگاه</b>'+(n!==tot?' از '+fa(tot):'')+' برای '+(p?p.title:c.name)+(m.min?' · قیمت از '+fa(Math.round(m.min/1000))+' تا '+fa(Math.round(m.max/1000))+' هزار تومان':'');
  }
  var INST = NQ.INSTALLMENT_TYPES, LINKS = NQ.LINKS;
  function instName(x){ return (INST[x.t]||{name:x.t}).name; }
  function otherInst(st){ return (st.installments||[]).filter(function(x){return x.t!=='torobpay'}); }
  /* آیکون پرداخت قسطی (روش‌های غیر از ترب‌پی)؛ پشت نام فروشگاه می‌آید */
  function payIcons(st){
    var o = otherInst(st);
    return o.length ? tipSpan('pay ins', TIPS.installment(o), IC.installment) : '';
  }
  /* سمت راست نام فروشگاه فقط یکی: ترب‌پی (که یعنی ضمانت ترب هم دارد) یا ضمانت ترب */
  function badgeHTML(st){
    if(st.torobpay) return '<span class="pay tp" role="link" tabindex="-1" aria-label="'+esc(TIPS.torobpay)+'" data-tip="'+esc(TIPS.torobpay)+'" data-href="'+LINKS.torobpay+'">'+IC.torobpay+'</span>';
    return guaranteeHTML(st);
  }
  /* امتیاز فروشگاه + سابقه در ترب */
  function rateHTML(st){
    if(!st.rating) return '';
    return '<span class="rate" aria-label="امتیاز '+fa1(st.rating)+' از ۵، '+fa(st.years)+' سال در ترب">'+IC.star+'<b>'+fa1(st.rating)+'</b><small>('+fa(st.years)+' سال در ترب)</small></span>';
  }
  /* متن راهنمای آیکون‌ها (با hover یا کلیک بالای آیکون نمایش داده می‌شود) */
  var TIPS = {
    torobpay: 'ترب‌پی: خرید قسطی، پرداخت در ۴ قسط بدون کارمزد. فروشگاه‌های ترب‌پی ضمانت ترب هم دارند. برای اطلاعات بیشتر بزنید.',
    installment: function(list){ return 'خرید قسطی: '+list.map(function(x){return instName(x)+(x.terms?' ('+x.terms+')':'')}).join('، ')+'.'; },
    guarantee: 'ضمانت ترب: اگر خرید از این فروشگاه به مشکل بخورد، ترب پیگیری می‌کند. برای توضیحات کامل بزنید.',
    smart: 'پیشنهادی: بهترین انتخاب برای شما بر اساس معتبر بودن فروشگاه، ضمانت ترب و ترب‌پی، به‌روز بودن قیمت و قیمت مناسب.'
  };
  /* نشان ضمانت ترب (سمت راست نام فروشگاه) */
  function guaranteeHTML(st){
    if(!st.guarantee) return '';
    return '<span class="torob-guarantee" role="link" tabindex="-1" aria-label="'+esc(TIPS.guarantee)+'" data-tip="'+esc(TIPS.guarantee)+'" data-href="'+LINKS.guarantee+'">' +
      '<span class="styles_hologram__5u9vV" style="width:24px;height:24px"><span class="styles_star__jo3q8"><span class="styles_wavyPattern__3a8qy"><span class="styles_wavyPatternLight__7Ymlp"></span></span></span>' +
      '<span class="styles_torobLogo__rNXpC"><span class="styles_torobLogoLight__xQOQ_"></span></span></span></span>';
  }
  function tipSpan(cls, text, inner){ return '<span class="'+cls+'" role="img" tabindex="-1" aria-label="'+esc(text)+'" data-tip="'+esc(text)+'">'+inner+'</span>'; }
  function adTag(){ return '<span class="tag ad" aria-label="آگهی ترب">'+IC.ad+'آگهی</span>'; }
  function suggestLine(km, sid){
    var sug = Travel.suggest(km), cur = Travel.resolve(km, sid), own = Travel.modeFor(sid), msg = '', back = '';
    if(Travel.mode==='auto' && !own) msg = 'پیشنهاد: '+Travel.label(sug)+' — '+Travel.reason(sug)+'.';
    else {
      var d = Travel.minutes(cur,km)-Travel.minutes(sug,km);
      if(cur==='walk' && km>3){
        if(own){ msg = 'مسیر پیاده طولانی است؛'; back = ' <button type="button" class="link-btn tip-link" data-smode-reset="'+sid+'">بازگشت به روش کلی</button>'; }
        else msg = 'مسیر پیاده طولانی است؛ '+Travel.label(sug)+' مناسب‌تر است.';
      }
      else if(sug!==cur && d>=3) msg = 'با '+Travel.label(sug)+' حدود '+fa(d)+' دقیقه زودتر می‌رسید.';
    }
    return msg ? '<p class="mode-tip">'+IC.auto+'<span>'+msg+back+'</span></p>' : '';
  }
  /* زمان رسیدن با هر روش؛ هر کدام قابل انتخاب است و فقط برای همین فروشگاه اعمال می‌شود */
  function modesHTML(km, sid, from){
    var cur = Travel.resolve(km, sid), own = Travel.modeFor(sid), gen = Travel.resolve(km), sug = Travel.suggest(km),
        all = Travel.all(km), fast = all.slice().sort(function(a,b){return a.min-b.min})[0].id;
    var genName = Travel.mode==='auto' ? 'پیشنهادی ('+Travel.label(gen)+')' : Travel.label(gen);
    var note = own
      ? '<p class="mode-own">روش انتخابی پیش‌فرض شما <button type="button" class="link-btn gen-link" data-smode-reset="'+sid+'" title="بازگشت به روش کلی">'+genName+'</button> است و شما به‌صورت دستی <b>'+Travel.label(own)+'</b> را برای این فروشگاه انتخاب کرده‌اید.</p>'
      : '<p class="mode-hint">برای عوض کردن روش رفتن به همین فروشگاه، یکی از روش‌ها را بزنید.'+(from?' زمان‌ها از «'+esc(from)+'» حساب شده است.':'')+'</p>';
    var key = '<p class="mode-key"><span class="k-sug">'+IC.auto+'پیشنهادی</span>'+(own && gen!==cur ? '<span class="k-gen"><i></i>روش کلی شما</span>' : '')+'</p>';
    return '<div class="wide"><div class="modes" role="group" aria-label="زمان رسیدن با هر روش">'+all.map(function(x){
      var isSug = x.id===sug, isGen = own && x.id===gen && x.id!==cur;
      var t = Travel.label(x.id)+(x.id===fast?' (سریع‌ترین)':'')+(isSug?' · پیشنهادی':'')+(isGen?' · روش کلی شما':'');
      return '<button type="button" class="mode'+(x.id===cur?' on':'')+(x.id===fast?' fast':'')+(isSug?' sug':'')+(isGen?' gen':'')+'" data-smode="'+x.id+'" data-sid="'+sid+'" aria-pressed="'+(x.id===cur)+'" title="'+t+'">'+
        (isSug ? '<i class="m-sug" aria-hidden="true">'+IC.auto+'</i>' : '')+IC[x.id]+'<b>'+fa(x.min)+'</b><small>دقیقه</small><em>'+Travel.label(x.id)+'</em></button>';
    }).join('')+'</div>'+key+note+suggestLine(km, sid)+'</div>';
  }
  /* دکمه‌ها: استعلام قیمت (قرمز؛ اگر استعلام ترب برای فروشنده غیرفعال باشد «فقط تماس») · واتساپ · مشاهده روی نقشه · مسیریابی */
  function inqOn(st){ return st.inquiry!==false; }
  /* پیام‌رسان فروشگاه: واتساپ یا بله */
  function msgHTML(st){
    var m = st.messenger==='bale' && st.bale ? {href:'https://ble.ir/'+st.bale, ic:IC.bale, t:'پیام به فروشگاه در بله'} : {href:'https://wa.me/'+waNumber(st), ic:IC.whatsapp, t:'پیام به فروشگاه در واتساپ'};
    return '<a class="act wa" href="'+m.href+'" target="_blank" rel="noopener" aria-label="'+m.t+'" data-hint="'+m.t+'">'+m.ic+'</a>';
  }
  function actsHTML(sid, st, km, plan){
    var inq = inqOn(st), multi = st.phones.length>1;
    return '<div class="acts">'+
      (inq ? '<button type="button" class="act call" data-inq="'+sid+'" aria-haspopup="dialog">'+IC.inquiry+'<span>استعلام قیمت</span></button>'
           : '<button type="button" class="act call" data-call="'+sid+'"'+(multi?' aria-haspopup="dialog"':'')+' title="استعلام از طریق ترب برای این فروشنده فعال نیست">'+IC.phone+'<span>فقط تماس</span></button>')+
      msgHTML(st)+
      '<button type="button" class="act map" data-showmap="'+sid+'" aria-label="مشاهده روی نقشه" data-hint="مشاهده روی نقشه">'+IC.map+'</button>'+
      '<a class="act nav" href="'+routeURL(st, Travel.resolve(km, sid))+'" target="_blank" rel="noopener" aria-label="مسیریابی" data-hint="مسیریابی با '+Travel.label(Travel.resolve(km, sid))+' (در گوگل‌مپ)">'+IC.route+'</a>'+
      '</div>';
  }
  var CHEV = '<svg class="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
  function extLink(href, text){ return '<a class="ext" href="'+href+'" target="_blank" rel="noopener">'+text+IC.ext+'</a>'; }
  /* امتیاز فروشگاه: با کلیک، جزئیات ارزیابی ترب باز می‌شود */
  function scoreRowHTML(sid, st){
    if(!st.rating) return '';
    var open = !!state.scoreOpen[sid];
    var h = '<dt>امتیاز</dt><dd><button type="button" class="score-btn" data-score="'+sid+'" aria-expanded="'+open+'">'+rateHTML(st)+CHEV+'</button></dd>';
    if(open) h += '<dd class="wide-row score-det">' +
      '<p class="sd-head">امتیاز فروشگاه <span class="rate">'+IC.star+'<b>'+fa1(st.rating)+'</b></span> <small>('+fa(st.years)+' سال در ترب)</small></p>' +
      '<ul class="sd-list">' +
        '<li><span>فعالیت در ترب</span><b>حدود '+st.orders90+' سفارش در ۹۰ روز اخیر</b></li>' +
        '<li><span>پیگیری سفارش</span><b>'+(st.followups ? fa(st.followups)+' کاربر در ترب پیگیری سفارش ثبت کرده‌اند.' : 'کاربری در ترب پیگیری سفارش ثبت نکرده است.')+'</b></li>' +
      '</ul>' +
      '<p class="sd-links">'+extLink(st.profile, 'پروفایل فروشگاه')+extLink(LINKS.score, 'شیوه ارزیابی فروشگاه')+'</p></dd>';
    return h;
  }
  /* پرداخت: ترب‌پی جدا نوشته می‌شود؛ «پرداخت قسطی» دکمه است و همهٔ روش‌های قسطی را نشان می‌دهد */
  function payRowHTML(sid, st){
    var list = st.installments||[], open = !!state.payOpen[sid];
    var h = '<dt>پرداخت</dt><dd class="pays">' +
      (st.torobpay ? '<a class="paytag tp" href="'+LINKS.torobpay+'" target="_blank" rel="noopener">'+IC.torobpay+'ترب‌پی</a>' : '') +
      (list.length ? '<button type="button" class="paytag ins pay-more" data-paymore="'+sid+'" aria-expanded="'+open+'">'+IC.installment+'پرداخت قسطی · '+fa(list.length)+' روش'+CHEV+'</button>' : '') +
      (!list.length ? 'نقدی و کارتی' : '') + '</dd>';
    if(open && list.length) h += '<dd class="wide-row inst-list"><ul>'+list.map(function(x){
      var t = INST[x.t]||{name:x.t};
      return '<li class="inst-'+x.t+'"><span class="in-n">'+(x.t==='torobpay'?IC.torobpay:IC.installment)+'<b>'+t.name+'</b></span><span class="in-t">'+(x.terms||'')+'</span>'+(t.url?extLink(t.url,'اطلاعات بیشتر'):'')+'</li>';
    }).join('')+'</ul></dd>';
    return h;
  }
  /* ردیف گارانتی یا (برای کالای خوراکی) پوشش کالابرگ */
  function extraLabel(cat, x){
    if(isFood(cat)) return x && x.kb ? '<span class="kbl yes">'+IC.kalabarg+'پوشش کالابرگ</span>' : '<span class="kbl no">بدون کالابرگ</span>';
    var w = NQ.warrantyLabel(x); return w ? '<small class="it-war">'+w+'</small>' : '';
  }
  function extraRowHTML(cat, x){
    if(isFood(cat)) return '<dt>کالابرگ</dt><dd class="'+(x && x.kb ? 'kb-yes' : 'kb-no')+'">'+(x && x.kb ? IC.kalabarg+'پوشش دارد؛ با اعتبار کالابرگ قابل خرید است' : 'پوشش ندارد')+'</dd>';
    var w = NQ.warrantyLabel(x); return w ? '<dt>گارانتی</dt><dd class="war">'+w+'</dd>' : '';
  }
  function hostOf(u){ return String(u).replace(/^https?:\/\//,'').replace(/\/.*$/,''); }
  /* اینستاگرام، سایت فروشگاه و لینک خرید همین محصول از سایت */
  function linksRowHTML(st, buy){
    if(!st.instagram && !st.website) return '';
    return '<dt>لینک‌ها</dt><dd class="links">' +
      (st.instagram ? '<a class="soc" href="https://instagram.com/'+st.instagram+'" target="_blank" rel="noopener">'+IC.insta+'<span dir="ltr">@'+st.instagram+'</span></a>' : '') +
      (st.website ? '<a class="soc" href="'+st.website+'" target="_blank" rel="noopener">'+IC.globe+'<span dir="ltr">'+hostOf(st.website)+'</span></a>' : '') + '</dd>' +
      (buy && st.website ? '<dd class="wide-row"><a class="buy-link" href="'+buy+'" target="_blank" rel="noopener">'+IC.cart+'<span>خرید این محصول از سایت فروشگاه</span>'+IC.ext+'</a></dd>' : '');
  }
  /* نشانی: با کلیک روی متن یا آیکون کپی می‌شود */
  function addrHTML(addr){
    return '<span class="addr"><span class="addr-t" role="button" tabindex="0" data-copy="'+esc(addr)+'" data-hint="برای کپی نشانی بزنید">'+addr+'</span>' +
      '<button type="button" class="copy-btn" data-copy="'+esc(addr)+'" aria-label="کپی نشانی" data-hint="کپی نشانی">'+IC.copy+'</button></span>';
  }
  /* اطلاعات بیشتر یک فروشگاه (هم در کارت نتایج و هم در برنامهٔ سر زدن) */
  function storeDetHTML(sid, st, km, opt){
    opt = opt || {};
    return '<dl class="det'+(opt.plan?' pdet':'')+'"><dt>نشانی</dt><dd>'+addrHTML(st.addr)+'</dd>' +
      '<dt>ساعت کار</dt><dd>'+st.hours+' '+statusHTML(st,true)+'</dd>' +
      '<dt>تلفن</dt><dd class="tels">'+st.phones.map(function(p){return '<a class="tel" href="tel:'+toTel(p)+'" dir="ltr" aria-label="تماس با '+p+'">'+p+'</a>'}).join('<i class="rsep">·</i>')+'</dd>' +
      (opt.extraRow||'') +
      (st.fast ? '<dt>ارسال</dt><dd class="fastv">'+IC.truck+st.fast+'</dd>' : '') +
      linksRowHTML(st, opt.buy) +
      scoreRowHTML(sid, st) +
      payRowHTML(sid, st) +
      '<dd class="wide-row">'+actsHTML(sid, st, km, opt.plan)+'</dd>' +
      modesHTML(km, sid, opt.from) +
      (opt.notes||'') +
      '<dd class="wide-row det-foot"><button type="button" class="report-btn" data-report="'+sid+'">'+IC.flag+'<span>گزارش مشکل فروشگاه</span></button></dd></dl>';
  }
  function cardHTML(o,m,i){
    var sel = state.selected===o.sid && !state.compare, slot = slotOf(o.sid), infoOpen = sel || !!state.sinfo[o.sid];
    var tags = o.ad ? adTag() : '';
    if(o.extra && o.extra.kb) tags += '<span class="tag kb" data-hint="با اعتبار کالابرگ قابل خرید است">'+IC.kalabarg+'کالابرگ</span>';
    if(o.store.fast) tags += '<span class="tag fast" data-hint="'+esc(o.store.fast)+'">'+IC.truck+'ارسال فوری</span>';
    if(o.sid===m.best) tags += '<span class="tag best">ارزان‌ترین</span>';
    if(o.sid===m.near) tags += '<span class="tag near">نزدیک‌ترین</span>';
    var stale = o.hrs>=48 ? '<span class="stale">قیمت قدیمی</span>' : '';
    var cls = 'card '+o.stock+(sel?' sel':'')+(o.ad?' is-ad':'')+(slot?' slot-'+slot.toLowerCase():'');
    var saved = Plan.has(o.sid,state.cat);
    var saveLbl = saved ? 'برداشتن از برنامهٔ سر زدن' : 'ذخیره در برنامهٔ سر زدن';
    var saveBtn = '<button type="button" class="save-btn" data-save="'+o.sid+'" aria-pressed="'+saved+'" aria-label="'+saveLbl+'" title="'+saveLbl+'">' +
      '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/></svg></button>';
    var infoBtn = '<button type="button" class="info-btn" data-sinfo="'+o.sid+'" aria-expanded="'+infoOpen+'" aria-label="'+(infoOpen?'بستن اطلاعات فروشگاه':'اطلاعات کامل فروشگاه')+'" title="'+(infoOpen?'بستن اطلاعات':'اطلاعات کامل فروشگاه')+'">'+IC.info+'</button>';
    var h = '<li style="--i:'+Math.min(i||0,10)+'"><article class="'+cls+'" data-sid="'+o.sid+'">' +
      '<button type="button" class="card-main" data-sid="'+o.sid+'" aria-pressed="'+(sel||!!slot)+'">' +
        (state.compare ? '<span class="pickmark'+(slot?' '+slot.toLowerCase():'')+'">'+(slot?SLOT[slot]:'')+'</span>' : '') +
        '<span class="c-body">' +
          '<span class="c-row"><span class="c-nm">'+badgeHTML(o.store)+'<span class="c-name" data-full="'+esc(o.store.name)+'">'+o.store.name+'</span></span>'+payIcons(o.store)+tags+'</span>' +
          '<span class="c-var">'+(curProd()?'':'<span class="c-model" data-full="'+esc(o.title)+'">'+o.title+'</span><span>·</span>')+colorsHTML(o.colors)+(o.colors.length>1?'<small class="ncol">'+fa(o.colors.length)+' رنگ</small>':'')+rateHTML(o.store)+'</span>' +
          '<span class="c-meta"><span class="stock '+o.stock+'">'+STOCK[o.stock]+'</span>'+statusHTML(o.store)+'<span>'+fa1(o.km)+' کیلومتر</span>'+etaHTML(o.km,o.sid)+stale+'</span>' +
        '</span>' +
        '<span class="c-price'+longP(o.price)+'"><b>'+fa(o.price)+'</b><small>تومان</small>'+updHTML(o.hrs)+'</span>' +
      '</button>' + saveBtn + infoBtn;
    if(infoOpen){
      h += storeDetHTML(o.sid, o.store, o.km, {extraRow: extraRowHTML(state.cat, o.extra), buy: o.store.website ? o.store.website.replace(/\/$/,'')+'/search?q='+encodeURIComponent(o.title) : '', notes:
        (o.stock==='unsure' ? '<dd class="note">آخرین بروزرسانی موجودی '+ago(o.hrs)+' بوده است. پیش از رفتن تماس بگیرید.</dd>' : '') +
        (o.stock==='out' ? '<dd class="note">این فروشگاه فعلاً این محصول را ندارد.</dd>' : '')});
    }
    return h+'</article></li>';
  }
  function renderList(rows){
    var st0 = stage();
    if(st0==='pick'){cardsEl.innerHTML='';return}
    if(st0==='dir'){
      var ds = dirRows();
      cardsEl.innerHTML = ds.length ? ds.map(dirCardHTML).join('') : '<li class="empty">فروشگاهی در این منطقه پیدا نشد. <button type="button" class="link-btn" data-act="cleardir">پاک کردن منطقه</button></li>';
      return;
    }
    if(!rows.length){
      var msg;
      if(!state.cat) msg = qEl.value.trim() ? '«'+esc(qEl.value.trim())+'» در داده‌های نمونه نیست. یکی از محصولات بالا را امتحان کنید.' :
        'دنبال چه محصولی می‌گردید؟ اسمش را جستجو کنید یا از گزینه‌های بالا انتخاب کنید.' +
        '<span class="empty-acts"><button type="button" class="empty-btn" data-act="nearme">'+IC.pin+'فروشگاه‌های اطراف من</button><button type="button" class="empty-btn" data-act="allmap">'+IC.map+'همهٔ فروشگاه‌ها روی نقشه</button></span>';
      else msg = 'فروشگاهی با این فیلترها پیدا نشد. <button type="button" class="link-btn" data-act="clearf">حذف فیلترها</button>';
      cardsEl.innerHTML = '<li class="empty">'+msg+'</li>';
      return;
    }
    var m = meta();
    var sep = false;
    cardsEl.innerHTML = rows.map(function(o,i){
      var h = '';
      if(o.stock==='out' && !sep){ sep = true; h = '<li class="out-sep" role="separator" aria-label="فروشگاه‌های ناموجود"><span>ناموجود</span></li>'; }
      return h+cardHTML(o,m,i);
    }).join('');
  }
  function renderPins(rows) {
    var st0 = stage();
    if (st0 === 'none' || st0 === 'dir') {   // بدون محصول: نام فروشگاه‌ها
      MapView.renderPins((st0 === 'dir' ? dirRows() : Object.keys(STORES)).map(function (sid) {
        var st = STORES[sid], sel = state.selected === sid;
        return {sid: sid, lat: st.lat, lng: st.lng, cls: 'dir' + (sel ? ' sel' : ''), html: '<span class="pp"><span class="pt">' + esc(st.name) + '</span></span>',
                label: st.name, z: sel ? 4000 : 0, group: 'dir', fixed: sel, data: {sid: sid}};
      }), CLUSTER_SPEC);
      return;
    }
    if (stage() === 'pick') {   // پین خنثی: نام مدلی که هر فروشگاه دارد؛ کلیک = انتخاب همان مدل
      MapView.renderPins(offerRows().map(function (o) {
        return {sid: o.sid, lat: o.store.lat, lng: o.store.lng, cls: '', html: '<span class="pp"><span class="pt">' + esc(modelOf(o.title)) + '</span></span>',
                label: o.store.name + '، ' + o.title, z: 0, group: o.title, data: o};
      }), CLUSTER_SPEC);
      return;
    }
    var m = meta();
    MapView.renderPins(rows.map(function (o) {
      var slot = slotOf(o.sid), sel = state.selected === o.sid && !state.compare;
      return {
        sid: o.sid, lat: o.store.lat, lng: o.store.lng,
        cls: o.stock + (o.sid === m.best ? ' best' : '') + (slot ? ' slot-' + slot.toLowerCase() : '') + (sel ? ' sel' : '') + (Plan.has(o.sid, state.cat) ? ' saved' : ''),
        html: '<span class="pp">' + (slot ? '<b class="pl">' + SLOT[slot] + '</b>' : '') + fa(Math.round(o.price / 1000)) + (o.stock === 'unsure' ? '<sup>؟</sup>' : '') + '</span>',
        label: o.store.name + '، ' + fa(o.price) + ' تومان، ' + STOCK[o.stock],
        z: sel ? 4000 : slot ? 3000 : o.sid === m.best ? 1000 : 0,
        group: o.title, fixed: sel || !!slot, data: o
      };
    }), CLUSTER_SPEC);
  }
  /* ظاهر خوشه: تعداد فروشگاه + ارزان‌ترین قیمت (یا نام مدل در مرحلهٔ انتخاب محصول) */
  function clusterView(items) {
    var os = items.map(function (i) { return i.data; }), n = os.length;
    if (stage() === 'none' || stage() === 'dir') return {cls: '', html: '<span class="cl"><b class="cl-n">' + fa(n) + '</b><span class="cl-t">فروشگاه</span></span>', label: fa(n) + ' فروشگاه. برای بزرگ‌نمایی بزنید'};
    if (stage() === 'pick') {
      return {cls: '', html: '<span class="cl"><b class="cl-n">' + fa(n) + '</b><span class="cl-t">' + esc(modelOf(os[0].title)) + '</span></span>',
              label: fa(n) + ' فروشگاه با ' + os[0].title + '. برای بزرگ‌نمایی بزنید'};
    }
    var m = meta(), live = os.filter(function (o) { return o.stock !== 'out'; });
    var min = live.length ? Math.min.apply(null, live.map(function (o) { return o.price; })) : 0;
    var best = os.some(function (o) { return o.sid === m.best; }), saved = os.some(function (o) { return Plan.has(o.sid, state.cat); });
    return {
      cls: (best ? 'best ' : '') + (live.length ? '' : 'out ') + (saved ? 'saved' : ''),
      html: '<span class="cl"><b class="cl-n">' + fa(n) + '</b><span class="cl-t">' + (min ? '<small>از</small> ' + fa(Math.round(min / 1000)) : 'ناموجود') + '</span></span>',
      label: fa(n) + ' فروشگاه' + (min ? '، از ' + fa(min) + ' تومان' : '') + '. برای بزرگ‌نمایی بزنید'
    };
  }
  var CLUSTER_SPEC = {cluster: clusterView};
  function renderRoutes() {
    var lines = [], o = state.origin;
    function add(P, Q, cls, sid) { lines.push({from: P, to: Q, cls: cls, text: routeText(roadKm(P, Q), sid)}); }
    if (state.compare) {
      var A = state.picks.A && STORES[state.picks.A], B = state.picks.B && STORES[state.picks.B];
      if (A) add(o, A, 'a', state.picks.A);
      if (B) add(o, B, 'b', state.picks.B);
      if (A && B) add(A, B, 'ab');
    } else if (state.selected && STORES[state.selected]) {
      add(o, STORES[state.selected], 'sel', state.selected);
    }
    MapView.renderRoutes(lines);
  }
  function slotHTML(L,o,empty){
    var l = L.toLowerCase();
    if(!o) return '<div class="slot empty">'+lt(L)+'<span>'+(empty||'فروشگاه '+SLOT[L]+' را از لیست یا نقشه انتخاب کنید')+'</span></div>';
    return '<div class="slot '+l+'">' +
      '<div class="s-top">'+lt(L)+'<span class="s-name" data-full="'+esc(o.store.name)+'">'+o.store.name+'</span><button type="button" class="s-x" data-unpick="'+L+'" aria-label="حذف فروشگاه '+SLOT[L]+'">×</button></div>' +
      '<span class="c-var"><span class="c-model" data-full="'+esc(o.title)+'">'+o.title+'</span><span>·</span>'+colorsHTML(o.colors)+'</span>' +
      '<span class="s-price"><b>'+fa(o.price)+'</b> تومان</span>' +
      '<span class="stock '+o.stock+'">'+STOCK[o.stock]+'</span>' +
      '<span class="s-dist">'+fa1(o.km)+' کیلومتر تا شما · '+etaHTML(o.km,o.sid)+'</span></div>';
  }
  function tipsFor(A,B){
    var t = [], both = [['A',A],['B',B]];
    if(A.stock!=='out' && B.stock!=='out'){
      var d = Math.abs(A.price-B.price);
      if(d===0) t.push('قیمت دو فروشگاه برابر است.');
      else t.push(lt(A.price<B.price?'A':'B')+' '+fa(Math.round(d/1000))+' هزار تومان ارزان‌تر است.');
    }
    if(A.title!==B.title) t.push('مدل دو فروشگاه فرق دارد، پس قیمت‌ها را نمی‌شود یک‌به‌یک مقایسه کرد.');
    else if(A.colors.length && B.colors.length && !A.colors.some(function(c){return B.colors.indexOf(c)>-1})) t.push('رنگ‌های موجود در دو فروشگاه فرق دارد.');
    if(A.stock==='in' && B.stock==='in'){
      t.push('موجودی هر دو فروشگاه تأیید شده است.');
    } else {
      both.forEach(function(p){
        var o = p[1];
        if(o.stock==='unsure') t.push('موجودی '+lt(p[0])+' تأیید نشده (آخرین بروزرسانی '+ago(o.hrs)+'). پیش از رفتن می‌توانید تماس بگیرید: '+o.store.phone);
        if(o.stock==='out') t.push(lt(p[0])+' این محصول را ندارد.');
      });
      var sure = both.filter(function(p){return p[1].stock==='in'});
      if(sure.length===1) t.push('اگر اول به '+lt(sure[0][0])+' بروید که موجودی‌اش تأیید شده، شاید لازم نباشد به دیگری سر بزنید.');
      else if(!sure.length && A.stock!=='out' && B.stock!=='out') t.push('چون موجودی هیچ‌کدام تأیید نشده، سر زدن به هر دو شانس پیدا کردن محصول را بالا می‌برد.');
    }
    return t;
  }
  function renderCmp(){
    if(!state.compare || !state.cat || stage()!=='stores'){cmpEl.innerHTML='';return}
    var A = state.picks.A && offer(state.picks.A), B = state.picks.B && offer(state.picks.B);
    var h = '<section class="cmp" aria-label="مقایسهٔ دو فروشگاه"><div class="cmp-head"><h2>مقایسهٔ دو فروشگاه</h2><button type="button" class="cmp-close" id="cmpClose">بستن</button></div>' +
      '<div class="slots">'+slotHTML('A',A)+slotHTML('B',B)+'</div>';
    if(A && B){
      h += cmpFactsHTML(A,B);
    } else {
      h += '<p class="cmp-hint">'+(!A&&!B ? 'دو فروشگاه را انتخاب کنید تا قیمت، موجودی و مسیر را کنار هم ببینید.' : 'یک فروشگاه دیگر انتخاب کنید.')+'</p>';
    }
    cmpEl.innerHTML = h+'</section>';
  }
  function cmpFactsHTML(A,B){
      var ab = roadKm(A.store,B.store), firstA = A.km<=B.km;
      var f = firstA?'A':'B', s = firstA?'B':'A';
      var total = Math.min(A.km,B.km)+ab, other = Math.max(A.km,B.km)+ab, round = A.km+ab+B.km;
      return '<dl class="facts">' +
        '<div><dt>فاصلهٔ دو فروشگاه از هم</dt><dd>'+fa1(ab)+' کیلومتر · '+etaHTML(ab)+'</dd></div>' +
        '<div><dt>مسیر پیشنهادی</dt><dd><span class="chain">شما <i>←</i> '+lt(f)+' <i>←</i> '+lt(s)+'</span> · '+fa1(total)+' کیلومتر</dd></div>' +
        '<div><dt>زمان مسیر پیشنهادی</dt><dd><span class="eta">'+IC[Travel.resolve(Math.min(A.km,B.km))]+'<span>'+fa(Travel.minutesFor(Math.min(A.km,B.km))+Travel.minutesFor(ab))+' دقیقه</span></span></dd></div>' +
        '<div><dt>ترتیب برعکس</dt><dd>'+fa1(other)+' کیلومتر</dd></div>' +
        '<div><dt>رفت‌وبرگشت کامل</dt><dd>'+fa1(round)+' کیلومتر</dd></div>' +
        '</dl><ul class="tips">'+tipsFor(A,B).map(function(x){return '<li><span>'+x+'</span></li>'}).join('')+'</ul>';
  }
  /* ---------- مقایسه در برنامهٔ سر زدن (فقط کالاهای هم‌دسته) ---------- */
  function planStop(sid){ return Plan.stops.filter(function(x){return x.sid===sid})[0] || null; }
  function commonCats(a, b){
    var A = planStop(a), B = planStop(b); if(!A || !B) return [];
    return A.cats.filter(function(c){ return B.cats.indexOf(c)>-1; });
  }
  function pslot(sid){ return state.pPicks.A===sid?'A':state.pPicks.B===sid?'B':null; }
  function syncPlanPicks(){
    var p = state.pPicks;
    ['A','B'].forEach(function(k){ if(p[k] && !planStop(p[k])) p[k] = null; });
    if(!p.A && p.B){ p.A = p.B; p.B = null; }
    var cc = p.A && p.B ? commonCats(p.A, p.B) : (p.A ? planStop(p.A).cats : []);
    if(p.A && p.B && !cc.length) p.B = null;
    if(cc.indexOf(state.pCat)<0) state.pCat = cc[0] || null;
  }
  function planPick(sid){
    var p = state.pPicks;
    if(p.A===sid) p.A = null;
    else if(p.B===sid) p.B = null;
    else if(!p.A) p.A = sid;
    else {
      if(!commonCats(p.A, sid).length){
        toast('«'+STORES[sid].name+'» کالای هم‌دسته با «'+STORES[p.A].name+'» ندارد. فقط کالاهای یک دسته (مثلاً هر دو هدفون) را می‌شود مقایسه کرد.', 'warn');
        return;
      }
      p.B = sid;
    }
    syncPlanPicks(); renderAll();
    if(p.A && p.B){ fitPoints([state.origin, STORES[p.A], STORES[p.B]]); listTop(true); }
    else revealStore(sid);
  }
  function renderPlanCmp(){
    var el = $('#planCmp');
    if(state.tab!=='plan' || !state.planCmp){ el.innerHTML = ''; return; }
    syncPlanPicks();
    var p = state.pPicks, cat = state.pCat, c = catById(cat);
    var A = p.A && cat && offerIn(cat, p.A), B = p.B && cat && offerIn(cat, p.B);
    var h = '<section class="cmp" aria-label="مقایسهٔ دو فروشگاه در برنامه"><div class="cmp-head"><h2>مقایسهٔ دو فروشگاه'+(c?' · '+c.name:'')+'</h2><button type="button" class="cmp-close" data-pcmp-close>بستن</button></div>';
    var cc = p.A && p.B ? commonCats(p.A, p.B) : [];
    if(cc.length>1) h += '<div class="pcats" role="radiogroup" aria-label="دستهٔ مقایسه">'+cc.map(function(id){
      return '<button type="button" class="chip" role="radio" data-pcat="'+id+'" aria-checked="'+(id===cat)+'" aria-pressed="'+(id===cat)+'">'+catById(id).name+'</button>';
    }).join('')+'</div>';
    h += '<div class="slots">'+slotHTML('A',A,'فروشگاه اولی را از برنامه یا نقشه انتخاب کنید')+slotHTML('B',B,'فروشگاه دومی را انتخاب کنید'+(c?' (باید «'+c.name+'» داشته باشد)':''))+'</div>';
    h += A && B ? cmpFactsHTML(A,B) : '<p class="cmp-hint">'+(!A ? 'روی دو فروشگاه از برنامه بزنید. فقط فروشگاه‌هایی که کالای هم‌دسته دارند با هم مقایسه می‌شوند.' : 'یک فروشگاه دیگر با کالای هم‌دسته انتخاب کنید.')+'</p>';
    el.innerHTML = h+'</section>';
  }
  /* ---------- برنامهٔ سر زدن ---------- */
  var planList = $('#planList');
  var faD = function (t) { return String(t).replace(/\d/g, function (d) { return '۰۱۲۳۴۵۶۷۸۹'[d]; }); };
  function hm(m) { m = Math.round(m); var h = Math.floor(m / 60) % 24, mi = m % 60; return faD((h < 10 ? '0' : '') + h + ':' + (mi < 10 ? '0' : '') + mi); }
  function dur(m) {
    m = Math.round(m); if (m < 60) return fa(m) + ' دقیقه';
    var h = Math.floor(m / 60), r = m % 60; return fa(h) + ' ساعت' + (r ? ' و ' + fa(r) + ' دقیقه' : '');
  }
  function statusText(r) {
    if (r.status === 'open')   return 'باز است تا ' + hm(r.closeM);
    if (r.status === 'soon')   return fa(r.left) + ' دقیقه تا بسته شدن (' + hm(r.closeM) + ')';
    if (r.status === 'later')  return 'ساعت ' + hm(r.openM) + ' باز می‌شود';
    return 'تا رسیدن شما بسته است (تا ' + hm(r.closeM) + ')';
  }
  /* موجودی کلی فروشگاه در برنامه (بر اساس همهٔ کالاهای ذخیره‌شده در آن) */
  function planStockHTML(st){
    var ks = st.cats.map(function(cid){ var r = (OFFERS[cid]||[]).filter(function(x){return x[0]===st.sid})[0]; return r && r[4]; }).filter(Boolean);
    if(!ks.length) return '';
    var k, t;
    if(ks.every(function(x){return x==='in'})){ k = 'in'; t = STOCK.in; }
    else if(ks.every(function(x){return x==='out'})){ k = 'out'; t = STOCK.out; }
    else if(ks.indexOf('out')>-1){ k = 'out'; t = 'بخشی ناموجود'; }
    else { k = 'unsure'; t = STOCK.unsure; }
    return '<span class="stock '+k+'">'+t+'</span>';
  }
  /* کالاهای یک فروشگاه در برنامه، به شکل کارت محصول: نام / رنگ و گارانتی (یا کالابرگ) / قیمت.
     وقتی اطلاعات کارت باز است، تصویر محصول و دکمهٔ «مشاهدهٔ جزئیات محصول» هم می‌آید.
     دکمهٔ «سر زدم» سمت چپ عنوان اولین کالاست. اگر فروشگاه فقط یک کالا دارد، موجودی کنار نام فروشگاه است و × جدا لازم نیست. */
  function visitBtn(sid, done){
    return '<button type="button" class="visit-btn" data-act="done" data-sid="'+sid+'" aria-pressed="'+!!done+'">'+
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'+
      '<span>'+(done?'سر زدم':'سر زدم؟')+'</span></button>';
  }
  /* جزئیات محصول در برنامه: اول مشخصات کلی و لینک ترب، بعد (در صورت نیاز) مشخصات بیشتر */
  function planProdDetHTML(p, cat){
    return '<div class="ppd">' +
      (p.desc ? '<p class="sp-desc">'+esc(p.desc)+'</p>' : '') +
      ((p.specs||[]).length ? '<h4 class="sp-h">مشخصات کلیدی</h4>'+specsDL(p.specs) : '') +
      torobBtn(p) + fullSpecsBtn(p, cat) +
    '</div>';
  }
  function planItemsHTML(st, open, done) {
    var single = st.cats.length < 2;
    return st.cats.map(function (cid, idx) {
      var c = catById(cid), r = (OFFERS[cid] || []).filter(function (x) { return x[0] === st.sid; })[0];
      if (!c || !r) return '';
      var cols = [].concat(r[2]||[]), ex = extraLabel(cid, r[6]), p = (PRODS[cid]||[]).filter(function(x){return x.title===r[1]})[0];
      var rmBtn = single ? '' : '<button type="button" class="it-x" data-act="rmcat" data-sid="'+st.sid+'" data-cat="'+cid+'" aria-label="برداشتن «'+c.name+'» از این فروشگاه">×</button>';
      var stock = single ? '' : '<span class="stock '+r[4]+'">'+STOCK[r[4]]+'</span>';
      var visit = idx===0 ? visitBtn(st.sid, done) : '';
      var sub = (cols.length ? '<span class="it-c">'+colorsHTML(cols)+'</span>' : '') + ex + stock;
      var name = '<span class="it-title"><span class="it-t" data-full="'+esc(r[1])+'">'+esc(r[1])+'</span></span>';
      var price = '<div class="it-l2"><b class="it-price'+longP(r[3])+'">'+fa(r[3])+' <small>تومان</small></b>'+updHTML(r[5])+'</div>';
      if (open && p) {
        var ctx = 'plan:'+st.sid+':'+p.id, gx = state.gx && state.gx.key===ctx, dOpen = !!state.ppd[ctx];
        return '<li class="pc-item pv-item'+(r[4]==='out'?' out':'')+'"><div class="pv'+(gx?' gx':'')+'">' + gviewHTML(ctx) +
          '<div class="pv-main">' + thumbHTML('pv-img', p, cid, ctx, NQ.art(p.kind, cols[0] ? COLORS[cols[0]] : null)) +
            '<div class="pv-body"><div class="it-l1">'+name+visit+rmBtn+'</div>' +
              (sub ? '<div class="it-sub">'+sub+'</div>' : '') + price +
            '</div></div>' +
          '<button type="button" class="ppd-btn" data-ppd="'+ctx+'" aria-expanded="'+dOpen+'">'+ICON.info+'<span>مشاهدهٔ جزئیات محصول</span>'+CHEV+'</button>' +
          (dOpen ? planProdDetHTML(p, cid) : '') +
        '</div></li>';
      }
      return '<li class="pc-item'+(r[4]==='out'?' out':'')+'">' +
        '<div class="it-l1">'+name+visit+rmBtn+'</div>' +
        (sub ? '<div class="it-sub">'+sub+'</div>' : '') + price + '</li>';
    }).join('');
  }
  var ICON = {
    up: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 15l6-6 6 6"/></svg>',
    down: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>',
    rm: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    cmp: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 3l4 4-4 4"/><path d="M20 7H8"/><path d="M8 21l-4-4 4-4"/><path d="M4 17h12"/></svg>',
    info: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.6v.1"/></svg>'
  };
  function renderTabs() {
    var plan = state.tab === 'plan', st = stage();
    var rc = $('#resCount'), n = st==='none' ? 0 : st==='dir' ? dirRows().length : st==='pick' ? pickList().length : offerRows().length;
    rc.hidden = st==='none'; rc.textContent = fa(n);
    $('#toolbar').hidden = plan; $('#scroll').hidden = plan;
    $('#planbar').hidden = !plan; $('#planScroll').hidden = !plan;
    $('#tabResults').setAttribute('aria-selected', String(!plan));
    $('#tabPlan').setAttribute('aria-selected', String(plan));
  }
  function renderPlan() {
    var n = Plan.count();
    $('#planCount').textContent = fa(n);
    $('#planClear').hidden = !n;
    Array.prototype.forEach.call(document.querySelectorAll('#planSort button'), function (b) {
      b.setAttribute('aria-checked', String(b.getAttribute('data-pmode') === Plan.mode));
    });
    $('#departNow').setAttribute('aria-pressed', String(!Plan.depart));
    var dt = $('#departTime'); if (document.activeElement !== dt) dt.value = Plan.depart || '';
    if (state.tab !== 'plan') return;

    Plan.applyMode(state.origin);
    var S = lastSched = Plan.schedule(state.origin);

    var sum = $('#planSummary');
    if (!n) sum.textContent = 'هنوز فروشگاهی ذخیره نشده است.';
    else sum.innerHTML = '<b>' + fa(S.active) + ' توقف</b>' + (S.active ? ' · ' + fa1(S.totalKm) + ' کیلومتر · حدود ' + dur(S.totalMin) + ' · پایان ≈ ' + hm(S.end) : ' (همه انجام شده)') +
      (Plan.mode === 'manual' ? ' · ترتیب دستی' : '');

    var closed = [], later = [];
    S.rows.forEach(function (r) { if (r.status === 'closed') closed.push(r.S.name); else if (r.status === 'later') later.push(r.S.name); });
    var al = $('#planAlert'), msg = '';
    if (closed.length) msg += 'تا رسیدن شما بسته است: ' + closed.join('، ') + '. ';
    if (later.length) msg += 'هنوز باز نشده (باید صبر کنید): ' + later.join('، ') + '. ';
    if (msg) msg += 'ساعت حرکت را عوض کنید یا ترتیب را تغییر دهید.';
    al.textContent = msg; al.hidden = !msg;

    if (!n) {
      planList.innerHTML = '<li class="empty">در «نتایج جستجو» روی نشانِ هر فروشگاه بزنید تا به برنامه اضافه شود. می‌توانید چند فروشگاه را برای چند محصول مختلف ذخیره کنید و با یک مسیر به همه سر بزنید.</li>';
      return;
    }
    var prev = 'موقعیت شما';
    planList.innerHTML = S.rows.map(function (r, i) {
      var sid = r.st.sid, sel = state.planSel === sid, open = !!state.planInfo[sid];
      var canUp = i > 0 && S.rows[i - 1].done === r.done, canDn = i < S.rows.length - 1 && S.rows[i + 1].done === r.done;
      var ps = state.planCmp ? pslot(sid) : null;
      var cls = 'pcard' + (r.done ? ' done' : ' st-' + r.status) + (sel ? ' sel' : '') + (open ? ' open' : '') + (ps ? ' slot-' + ps.toLowerCase() : '') + (state.planCmp ? ' picking' : '');
      var leg = '', badge = '', from = prev, km = r.done ? roadKm(state.origin, r.S) : r.km;
      if (!r.done) {
        leg = '<p class="pc-leg">از ' + prev + ': ' + fa1(r.km) + ' کیلومتر · <span class="eta">' + IC[r.mode] + '<span>' + dur(r.tm) + '</span></span> · رسیدن حدود <b>' + hm(r.arrive) + '</b></p>';
        badge = '<span class="badge ' + r.status + '">' + statusText(r) + '</span>';
        prev = r.S.name;
      } else { badge = '<span class="badge done">انجام شد</span>'; from = 'موقعیت شما'; }
      return '<li style="--i:' + Math.min(i, 10) + '"><article class="' + cls + '" data-sid="' + sid + '">' +
        '<div class="pc-top">' + (state.planCmp ? '<span class="pickmark' + (ps ? ' ' + ps.toLowerCase() : '') + '">' + (ps ? SLOT[ps] : '') + '</span>' : '<span class="pn">' + (r.done ? '✓' : fa(r.n)) + '</span>') +
          '<div class="pc-info"><div class="pc-nr"><span class="c-nm">' + badgeHTML(r.S) + '<button type="button" class="pc-name" data-act="focus" data-sid="' + sid + '" aria-pressed="' + sel + '" data-full="' + esc(r.S.name) + '">' + r.S.name + '</button>' + payIcons(r.S) + '</span>' +
            '<span class="pc-st">' + badge + planStockHTML(r.st) + '</span></div></div>' +
          '<div class="pc-acts">' +
            '<button type="button" class="icon-btn sm" data-act="up" data-sid="' + sid + '" aria-label="بالاتر ببر (اولویت بیشتر)" title="بالاتر"' + (canUp ? '' : ' disabled') + '>' + ICON.up + '</button>' +
            '<button type="button" class="icon-btn sm" data-act="down" data-sid="' + sid + '" aria-label="پایین‌تر ببر" title="پایین‌تر"' + (canDn ? '' : ' disabled') + '>' + ICON.down + '</button>' +
            '<button type="button" class="icon-btn sm" data-act="rm" data-sid="' + sid + '" aria-label="حذف از برنامه" title="حذف">' + ICON.rm + '</button>' +
          '</div></div>' +
        leg +
        '<ul class="pc-items">' + planItemsHTML(r.st, open, r.done) + '</ul>' +
        (open ? storeDetHTML(sid, r.S, km, {plan: true, from: from}) : '') +
        '</article></li>';
    }).join('');
  }
  function renderPlanMap() {
    var S = lastSched, items = [], lines = [], pos = state.origin;
    var P = state.planCmp ? state.pPicks : null;
    S.rows.forEach(function (r) {
      var sel = state.planSel === r.st.sid, ps = P ? pslot(r.st.sid) : null;
      items.push({
        sid: r.st.sid, lat: r.S.lat, lng: r.S.lng,
        cls: 'plan ' + (r.done ? 'done' : 'st-' + r.status) + (sel ? ' sel' : '') + (ps ? ' slot-' + ps.toLowerCase() : ''),
        html: '<span class="pp"><b class="pn">' + (r.done ? '✓' : fa(r.n)) + '</b><span class="pn-name" data-full="' + esc(r.S.name) + '">' + r.S.name + '</span></span>',
        label: (r.done ? 'انجام شد: ' + r.S.name : fa(r.n) + '. ' + r.S.name + '، ' + statusText(r)),
        z: ps ? 3000 : sel ? 4000 : r.done ? 0 : 1500
      });
      if (!r.done && !(P && P.A && P.B)) { lines.push({from: pos, to: r.S, cls: 'plan', text: routeText(r.km, r.st.sid)}); pos = r.S; }
    });
    if (P && P.A && P.B) {   // در حالت مقایسه: مسیر شما ← اولی، شما ← دومی و فاصلهٔ دو فروشگاه
      var A = STORES[P.A], B = STORES[P.B], o = state.origin;
      lines.push({from: o, to: A, cls: 'a', text: routeText(roadKm(o, A), P.A)});
      lines.push({from: o, to: B, cls: 'b', text: routeText(roadKm(o, B), P.B)});
      lines.push({from: A, to: B, cls: 'ab', text: routeText(roadKm(A, B))});
    }
    MapView.renderPins(items);
    MapView.renderRoutes(lines);
  }
  /* دکمهٔ «اطلاعات کامل» کنار نشان ذخیره: بدون انتخاب کارت، اطلاعات فروشگاه را باز/بسته می‌کند */
  function toggleStoreInfo(sid){
    var open = (state.selected===sid && !state.compare) || !!state.sinfo[sid];
    if(open){ delete state.sinfo[sid]; if(state.selected===sid) state.selected = null; }
    else { state.sinfo[sid] = true; setSheet('full'); }
    renderAll();
    var b = cardsEl.querySelector('[data-sinfo="'+sid+'"]'); if(b) b.focus({preventScroll:true});
    if(!open) requestAnimationFrame(function(){
      var el = cardsEl.querySelector('.card[data-sid="'+sid+'"]'); if(el) el.scrollIntoView({block:'nearest',behavior:reduced?'auto':'smooth'});
    });
  }
  function toggleSave(sid) {
    if (!state.cat) return;
    var saved = Plan.toggle(sid, state.cat), c = catById(state.cat);
    toast(saved ? 'برای «' + c.name + '» به برنامهٔ سر زدن اضافه شد.' : 'از برنامهٔ سر زدن برداشته شد.', saved ? 'success' : 'info');
    renderAll();
    var again = cardsEl.querySelector('.save-btn[data-save="' + sid + '"]'); if (again) again.focus();
  }
  function setTab(t) {
    if (state.tab === t) return;
    state.tab = t; state.planSel = null;
    setSheet(autoSheet());
    renderAll(); fitCurrent();
  }

  /* ---------- مرحلهٔ انتخاب مدل + نوار محصول ---------- */
  var CHEV_DOWN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
  var CHEV_GO = '<svg class="pr-go" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg>';
  /* cat: دسته (پیش‌فرض دستهٔ فعلی) · raw: بدون فیلترهای صفحهٔ فهرست (برای تربچت) */
  function prodStats(p, cat, raw){
    cat = cat || state.cat;
    var rows = OFFERS[cat].filter(function(r){return r[1]===p.title}).map(function(r){return mk(r, cat)}).filter(raw ? Boolean : passes);
    var live = rows.filter(function(o){return o.stock!=='out'});
    var cnt = {}, colors = [];
    rows.forEach(function(o){o.colors.forEach(function(c){cnt[c]=(cnt[c]||0)+1; if(colors.indexOf(c)<0) colors.push(c)})});
    var main = colors.slice().sort(function(a,b){return cnt[b]-cnt[a]})[0];
    var prices = live.map(function(o){return o.price}), kms = live.map(function(o){return o.km});
    return {n:rows.length, live:live.length, colors:colors, main:main,
            min:prices.length?Math.min.apply(null,prices):0, max:prices.length?Math.max.apply(null,prices):0, near:kms.length?Math.min.apply(null,kms):0};
  }
  function artHTML(p,s){
    if(p.img) return '<img src="'+esc(p.img)+'" alt="" loading="lazy">';
    return NQ.art ? NQ.art(p.kind, COLORS[s.main]||'#8C9692') : '';
  }
  /* ---------- تصویرهای محصول: چند تصویر (هر رنگ + نماهای دیگر) یا عکس‌های واقعی imgs ---------- */
  var VIEWCAP = {box:'جعبه', grain:'نمای نزدیک'};
  function prodOf(cat, pid){ return (PRODS[cat]||[]).filter(function(x){return x.id===pid})[0] || null; }
  function prodColorsAll(p, cat){
    var cols = [];
    (OFFERS[cat]||[]).forEach(function(r){ if(r[1]===p.title) [].concat(r[2]||[]).forEach(function(c){ if(cols.indexOf(c)<0) cols.push(c); }); });
    return cols;
  }
  function prodImages(p, cat){
    if(p.imgs && p.imgs.length) return p.imgs.map(function(u){ return {html:'<img src="'+esc(u)+'" alt="'+esc(p.title)+'" loading="lazy">', cap:''}; });
    var cols = prodColorsAll(p, cat), out = [];
    (cols.length ? cols : [null]).forEach(function(c){ out.push({html:NQ.art(p.kind, c ? COLORS[c] : null), cap:c||''}); });
    (p.views||['box']).forEach(function(k){ out.push({html:NQ.art(k, cols[0] ? COLORS[cols[0]] : null), cap:VIEWCAP[k]||''}); });
    return out;
  }
  /* تصویر کوچک قابل کلیک (با کلیک بزرگ می‌شود؛ کارت پشتش انتخاب نمی‌شود) */
  function thumbHTML(cls, p, cat, ctx, inner){
    var n = prodImages(p, cat).length;
    return '<span class="'+cls+' gthumb" role="button" tabindex="0" data-gal="'+ctx+'" data-gp="'+p.id+'" data-gc="'+cat+'" aria-label="بزرگ کردن تصویر '+esc(p.title)+'" data-hint="'+(n>1?fa(n)+' تصویر · ':'')+'برای بزرگ‌نمایی بزنید">'+inner+(n>1?'<i class="gcount">'+fa(n)+'</i>':'')+'</span>';
  }
  /* تصویر بزرگ‌شده (تمام‌عرض) با دکمه‌های کوچک کردن، قبلی/بعدی و تمام‌صفحه */
  function gviewHTML(ctx){
    var g = state.gx; if(!g || g.key!==ctx) return '';
    var p = prodOf(g.cat, g.pid); if(!p) return '';
    var imgs = prodImages(p, g.cat), n = imgs.length, i = Math.min(g.i, n-1), im = imgs[i];
    return '<div class="gview" data-gview="'+ctx+'" role="group" aria-label="تصویرهای '+esc(p.title)+'">' +
      '<div class="gv-stage" data-gfull="'+ctx+'" role="button" tabindex="0" aria-label="نمایش تمام‌صفحه">'+im.html+'</div>' +
      '<button type="button" class="gv-btn gv-min" data-gmin aria-label="کوچک کردن تصویر" data-hint="کوچک کردن">'+IC.shrink+'</button>' +
      '<button type="button" class="gv-btn gv-fs" data-gfull="'+ctx+'" aria-label="نمایش تمام‌صفحه" data-hint="تمام‌صفحه">'+IC.expand+'</button>' +
      (n>1 ? '<button type="button" class="gv-btn gv-prev" data-gstep="-1" aria-label="تصویر قبلی">'+IC.chevR+'</button>' +
             '<button type="button" class="gv-btn gv-next" data-gstep="1" aria-label="تصویر بعدی">'+IC.chevL+'</button>' : '') +
      '<span class="gv-count">'+fa(i+1)+' / '+fa(n)+(im.cap?' · '+esc(im.cap):'')+'</span>' +
      (n>1 ? '<span class="gv-dots" aria-hidden="true">'+imgs.map(function(_,k){return '<i'+(k===i?' class="on"':'')+'></i>'}).join('')+'</span>' : '') +
    '</div>';
  }
  function swatches(cols){
    return '<span class="dots" aria-label="رنگ‌ها: '+cols.join('، ')+'">'+cols.map(function(c){return '<i class="sw" style="background:'+COLORS[c]+'" title="'+c+'"></i>'}).join('')+'</span>';
  }
  var lastProds = '', lastBar = '', lastPCmp = '';
  var MAX_CMP = 5;   // حداکثر محصول در یک مقایسه
  /* شمارهٔ محصول در مقایسه (۱ تا ۵) یا ۰ */
  function pslotOf(id){ return state.pcmp.indexOf(id) + 1; }
  function nbHTML(n){ return '<b class="nb nb-'+n+'">'+fa(n)+'</b>'; }
  function cmpBtnHTML(id, n){
    var full = !n && state.pcmp.length>=MAX_CMP;
    var lbl = n ? 'برداشتن از مقایسه' : full ? 'حداکثر '+fa(MAX_CMP)+' محصول را می‌شود مقایسه کرد' : 'افزودن به مقایسه';
    return '<button type="button" class="cmp-ic'+(n?' on':'')+'" data-pcmp="'+id+'" aria-pressed="'+!!n+'" aria-label="'+lbl+'" title="'+lbl+'">' +
      (n ? nbHTML(n) : ICON.cmp) + '</button>';
  }
  /* محصولات قابل‌نمایش (حداقل یک فروشگاهِ سازگار با فیلترها) به ترتیبِ انتخاب‌شده */
  function pickList(){
    var list = prodsOf(state.cat).map(function(p){return {p:p,s:prodStats(p)}}).filter(function(x){return x.s.n>0});
    var gmin = Math.min.apply(null, list.map(function(x){return x.s.min||Infinity}));
    var key = {
      price:function(x){return x.s.min||Infinity},
      near:function(x){return x.s.live?x.s.near:Infinity},
      smart:function(x){return x.s.min ? x.s.min/(gmin||1)+x.s.near*.06 : Infinity}
    }[state.sort];
    return list.sort(function(a,b){return key(a)-key(b)});
  }
  function renderProducts(){
    var html = '';
    if(stage()==='pick'){
      var list = pickList();
      var best = null, many = list.length>1;
      list.forEach(function(x){if(x.s.min && (!best || x.s.min<best.s.min)) best = x});
      html = list.map(function(x,i){
        var p = x.p, s = x.s, open = !!state.pinfo[p.id], slot = pslotOf(p.id);
        var price = s.min ? '<span class="pr-price'+longP(s.min)+'"><small>از</small><b>'+fa(s.min)+'</b><small>تومان</small></span>' : '<span class="pr-price"><small>فعلاً ناموجود</small></span>';
        var range = s.min ? (s.max>s.min ? 'از '+fa(s.min)+' تا '+fa(s.max)+' تومان' : fa(s.min)+' تومان') : 'فعلاً در هیچ فروشگاهی موجود نیست';
        var ctx = 'list:'+p.id, gx = state.gx && state.gx.key===ctx;
        return '<li style="--i:'+i+'"><article class="prod'+(open?' open':'')+(gx?' gx':'')+(slot?' in-cmp':'')+'" data-id="'+p.id+'">' + gviewHTML(ctx) +
          '<button type="button" class="prod-main" data-prod="'+p.id+'" aria-label="دیدن فروشگاه‌های '+esc(p.title)+'">' +
            thumbHTML('pr-img', p, state.cat, ctx, artHTML(p,s)) +
            '<span class="pr-body">' +
              '<span class="pr-row"><span class="pr-name" data-full="'+esc(p.title)+'">'+esc(p.title)+'</span>'+(best===x && many ? '<span class="tag best">ارزان‌ترین</span>' : '')+'</span>' +
              '<span class="pr-desc">'+esc(p.tagline||'')+'</span>' +
              price +
              '<span class="pr-meta">'+swatches(s.colors)+'<span>'+fa(s.n)+' فروشگاه</span>'+(s.live ? '<span>نزدیک‌ترین '+fa1(s.near)+' کیلومتر</span>'+etaHTML(s.near) : '')+'</span>' +
            '</span>' + CHEV_GO + '</button>' +
          '<div class="pr-foot">' +
            '<button type="button" class="pr-more" data-pinfo="'+p.id+'" aria-expanded="'+open+'" aria-controls="pd-'+p.id+'">'+ICON.info+'<span>مشاهدهٔ جزئیات</span>'+CHEV_DOWN+'</button>' +
            (many ? cmpBtnHTML(p.id, slot) : '') +
          '</div>' +
          '<div class="pr-det" id="pd-'+p.id+'"'+(open?'':' hidden')+'>' +
            '<p class="pr-range"><span>قیمت در فروشگاه‌ها</span><b>'+range+'</b></p>' +
            infoHTML(p,s) +
            '<button type="button" class="pr-go-btn" data-prod="'+p.id+'">دیدن '+fa(s.n)+' فروشگاه روی نقشه'+CHEV_GO+'</button>' + torobBtn(p) +
          '</div>' +
        '</article></li>';
      }).join('');
    }
    if(stage()==='pick' && !html) html = '<li class="empty">محصولی با این فیلترها پیدا نشد. <button type="button" class="link-btn" data-act="clearf">حذف فیلترها</button></li>';
    if(html!==lastProds){prodsEl.innerHTML = html; lastProds = html}
  }
  /* ---------- مقایسهٔ چند محصول (تا ۵) ---------- */
  /* جدول مقایسه: ستون اول عنوان ردیف (چسبان)، بعد یک ستون برای هر محصول؛ اگر جا نشود افقی اسکرول می‌شود.
     rows: [{l, v:[...], win:[اندیس برنده‌ها], diff, head, raw}] */
  function cmpGridHTML(items, rows, cls){
    var n = items.length;
    return '<div class="cgrid-wrap'+(cls?' '+cls:'')+'"><div class="cgrid sx-list" role="table" style="--n:'+n+'">' +
      '<div class="cg-row cg-head" role="row"><span class="cg-l" role="columnheader"></span>' + items.map(function(x, i){
        var nm = x.name || modelOf(x.p.title);
        return '<span class="cg-v" role="columnheader">'+nbHTML(i+1)+'<span class="cg-hname" data-full="'+esc(x.name || x.p.title)+'">'+esc(nm)+'</span></span>';
      }).join('') + '</div>' +
      rows.map(function(r){
        if(r.head) return '<div class="cg-row cg-sec sx-head" role="row" id="sxg-'+slug(r.l)+'"><span role="rowheader">'+esc(r.l)+'</span></div>';
        return '<div class="cg-row sx-row'+(r.diff?' diff':'')+'" role="row" data-t="'+esc(nw(r.l+' '+r.v.join(' ')))+'"><span class="cg-l" role="rowheader">'+esc(r.l)+'</span>' +
          r.v.map(function(v, i){ return '<span class="cg-v'+((r.win||[]).indexOf(i)>-1?' win':'')+'" role="cell">'+(r.raw ? v : esc(v))+'</span>'; }).join('') + '</div>';
      }).join('') + '<p class="sx-empty" hidden>موردی با این جستجو پیدا نشد.</p></div></div>';
  }
  /* اندیس بهترین‌ها: lowWins = کمتر بهتر (قیمت، فاصله) */
  function winners(vals, lowWins){
    var ok = vals.filter(function(v){ return v>0; }); if(ok.length<2) return [];
    var best = lowWins ? Math.min.apply(null, ok) : Math.max.apply(null, ok);
    if(ok.every(function(v){ return v===best; })) return [];
    return vals.map(function(v, i){ return v===best ? i : -1; }).filter(function(i){ return i>-1; });
  }
  function allSame(vals){ return vals.every(function(v){ return v===vals[0]; }); }
  /* ردیف‌های خلاصه (قیمت، فروشگاه‌ها، نزدیک‌ترین، رنگ‌ها) + مشخصات کلیدی */
  function cmpRows(items, full){
    var rows = [], S = items.map(function(x){ return x.s; });
    rows.push({l:'کمترین قیمت', v:S.map(function(s){ return s.min ? fa(s.min)+' تومان' : 'ناموجود'; }), win:winners(S.map(function(s){return s.min}), true)});
    if(full) rows.push({l:'بیشترین قیمت', v:S.map(function(s){ return s.max ? fa(s.max)+' تومان' : '—'; })});
    rows.push({l:'فروشگاه‌ها', v:S.map(function(s){ return fa(s.n)+' ('+fa(s.live)+' موجود)'; }), win:winners(S.map(function(s){return s.live}), false)});
    rows.push({l:'نزدیک‌ترین', v:S.map(function(s){ return s.live ? fa1(s.near)+' کیلومتر' : '—'; }), win:winners(S.map(function(s){return s.live ? s.near : 0}), true)});
    rows.push({l:'رنگ‌ها', v:S.map(function(s){ return s.colors.length ? swatches(s.colors) : '—'; }), raw:true});
    return rows;
  }
  function specRows(items, groupsMode){
    var rows = [];
    if(!groupsMode){
      var labels = [];
      items.forEach(function(x){ (x.p.specs||[]).forEach(function(r){ if(labels.indexOf(r[0])<0) labels.push(r[0]); }); });
      labels.forEach(function(l){
        var v = items.map(function(x){ var r = (x.p.specs||[]).filter(function(y){return y[0]===l})[0]; return r ? r[1] : '—'; });
        rows.push({l:l, v:v, diff:!allSame(v)});
      });
      return rows;
    }
    /* همهٔ گروه‌های مشخصات همهٔ محصولات، ادغام‌شده به ترتیب ظاهر شدن */
    var groups = [], gmap = {};
    items.forEach(function(x, side){
      fullSpecs(x.p).forEach(function(g){
        var G = gmap[g.g]; if(!G){ G = gmap[g.g] = {g:g.g, labels:[], vals:{}}; groups.push(G); }
        g.items.forEach(function(it){ if(G.labels.indexOf(it[0])<0) G.labels.push(it[0]); (G.vals[it[0]] = G.vals[it[0]] || {})[side] = it[1]; });
      });
    });
    groups.forEach(function(G){
      rows.push({l:G.g, head:true});
      G.labels.forEach(function(l){ var v = items.map(function(_, i){ return G.vals[l][i] || '—'; }); rows.push({l:l, v:v, diff:!allSame(v)}); });
    });
    return rows;
  }
  /* نکته‌های کلیدی: ارزان‌ترین، بیشترین فروشگاه، نزدیک‌ترین، تعداد تفاوت‌ها */
  function cmpTips(items, diffs){
    var tips = [], S = items.map(function(x){ return x.s; }), name = function(i){ return nbHTML(i+1)+' '+esc(modelOf(items[i].p.title)); };
    var w = winners(S.map(function(s){return s.min}), true);
    if(w.length===1){ var mx = Math.max.apply(null, S.map(function(s){return s.min||0})); var gap = mx-S[w[0]].min; tips.push(name(w[0])+' ارزان‌ترین است؛ تا '+(gap>=1e6 ? fa(Math.round(gap/1e5)/10)+' میلیون' : fa(Math.round(gap/1000))+' هزار')+' تومان ارزان‌تر از گران‌ترین.'); }
    var ws = winners(S.map(function(s){return s.live}), false); if(ws.length===1) tips.push(name(ws[0])+' در فروشگاه‌های بیشتری موجود است.');
    var wn = winners(S.map(function(s){return s.live ? s.near : 0}), true); if(wn.length===1) tips.push('نزدیک‌ترین فروشگاه را '+name(wn[0])+' دارد.');
    if(diffs) tips.push(fa(diffs)+' ویژگی با هم فرق دارد (ردیف‌های پررنگ).');
    return tips;
  }
  function renderPCmp(){
    var html = '';
    var items = state.pcmp.map(prodById).filter(Boolean).map(function(p){ return {p:p, s:prodStats(p)}; });
    if(stage()==='pick' && items.length){
      html = '<section class="cmp pcmp" aria-label="مقایسهٔ محصولات"><div class="cmp-head"><h2>مقایسهٔ محصولات <small>('+fa(items.length)+' از '+fa(MAX_CMP)+')</small></h2><button type="button" class="cmp-close" id="pcmpClose">بستن</button></div>' +
        '<div class="pc-heads">' + items.map(function(x, i){
          return '<div class="pc-h">' +
            '<div class="s-top">'+nbHTML(i+1)+'<span class="s-name" data-full="'+esc(x.p.title)+'">'+esc(modelOf(x.p.title))+'</span><button type="button" class="s-x" data-punpick="'+x.p.id+'" aria-label="حذف '+esc(x.p.title)+' از مقایسه">×</button></div>' +
            '<span class="ps-img">'+artHTML(x.p, x.s)+'</span>' +
            (x.s.min ? '<span class="s-price"><small>از</small> <b>'+fa(x.s.min)+'</b></span>' : '<span class="s-price">ناموجود</span>') +
            '<button type="button" class="ps-go" data-prod="'+x.p.id+'">فروشگاه‌ها</button></div>';
        }).join('') + (items.length<MAX_CMP ? '<div class="pc-h pc-add"><span>'+ICON.cmp+'</span>با آیکون مقایسه، محصول دیگری اضافه کنید</div>' : '') + '</div>';
      if(items.length>1){
        var sr = specRows(items, false), diffs = sr.filter(function(r){return r.diff}).length;
        html += '<div class="cmp-mode" role="group" aria-label="نوع مقایسه"><button type="button" class="cm-btn" aria-pressed="true">مقایسهٔ کلیدی</button>' +
          '<button type="button" class="cm-btn" data-pcmp-full aria-haspopup="dialog">مقایسهٔ کامل'+IC.expand+'</button></div>' +
          cmpGridHTML(items, cmpRows(items).concat(sr));
        var tips = cmpTips(items, diffs);
        if(tips.length) html += '<ul class="tips">'+tips.map(function(x){return '<li><span>'+x+'</span></li>'}).join('')+'</ul>';
      }
      html += '</section>';
    }
    if(html!==lastPCmp){pcmpEl.innerHTML = html; lastPCmp = html}
  }
  /* مقایسهٔ کامل چند محصول (پاپ‌آپ): تصویر و نام هر محصول، خلاصه (قیمت، فروشگاه‌ها، رنگ‌ها، برند، توضیح) و همهٔ مشخصات */
  function fullCmpHTML(prods, cat){
    var items = prods.map(function(p){ return {p:p, s:prodStats(p, cat, !!cat)}; });
    var rows = [{l:'خلاصه', head:true}].concat(cmpRows(items, true));
    rows.push({l:'برند', v:items.map(function(x){ return x.p.brand || '—'; })});
    rows.push({l:'توضیح', v:items.map(function(x){ return x.p.desc || '—'; })});
    var sr = specRows(items, true);
    rows = rows.concat(sr);
    var groups = ['خلاصه'].concat(sr.filter(function(r){return r.head}).map(function(r){return r.l}));
    return '<div class="fc-heads" style="--n:'+items.length+'">' + items.map(function(x, i){
        return '<div class="fc-h">'+nbHTML(i+1)+'<span class="fc-img">'+artHTML(x.p, x.s)+'</span><b class="fc-name">'+esc(x.p.title)+'</b>'+torobBtn(x.p)+'</div>';
      }).join('') + '</div>' +
      specTools(groups, true) + cmpGridHTML(items, rows, 'fc-grid') +
      '<p class="sp-note">ردیف‌های پررنگ با هم فرق دارند. مشخصات نمونه است و فقط برای نمایش آورده شده.</p>';
  }
  /* ابزار مشخصات طولانی: جستجو، پرش به گروه‌ها و (در مقایسه) «فقط تفاوت‌ها» */
  /* نرمال‌سازی برای جستجو با حفظ فاصله‌ها؛ تطبیق از ابتدای کلمه (تا «رم» در «کیلوگرم» پیدا نشود) */
  function nw(t){ return ' '+String(t).replace(/ي/g,'ی').replace(/ك/g,'ک').replace(/\u200c/g,'').replace(/[۰-۹]/g,function(d){return '۰۱۲۳۴۵۶۷۸۹'.indexOf(d)}).replace(/[^\w\u0600-\u06FF.]+/g,' ').replace(/\s+/g,' ').toLowerCase().trim(); }
  function slug(t){ return String(t).replace(/[^\w\u0600-\u06FF]+/g,'-'); }
  function specTools(groups, cmp){
    return '<div class="sx-tools">' +
      '<label class="sx-search"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></svg>' +
        '<input type="search" class="sx-q" placeholder="جستجو در مشخصات (مثلاً رم، باتری)" aria-label="جستجو در مشخصات"></label>' +
      (cmp ? '<label class="sx-diff"><input type="checkbox" class="sx-d"> فقط تفاوت‌ها</label>' : '') +
      (groups.length>1 ? '<nav class="sx-nav" aria-label="گروه‌های مشخصات">'+groups.map(function(g){return '<a href="#sxg-'+slug(g)+'" class="sx-chip">'+esc(g)+'</a>'}).join('')+'</nav>' : '') +
    '</div>';
  }
  function filterSpecs(root){
    var q = nw((root.querySelector('.sx-q')||{}).value||''); if(q===' ') q = '';
    var d = (root.querySelector('.sx-d')||{}).checked, shown = 0, head = null, any = false;
    function closeHead(){ if(head) head.hidden = !any; }
    Array.prototype.forEach.call(root.querySelectorAll('.sx-head, .sx-row'), function(el){
      if(el.classList.contains('sx-head')){ closeHead(); head = el; any = false; return; }
      var ok = (!q || (' '+el.getAttribute('data-t')).indexOf(q)>-1) && (!d || el.classList.contains('diff'));
      el.hidden = !ok; if(ok){ any = true; shown++; }
    });
    closeHead();
    var em = root.querySelector('.sx-empty'); if(em) em.hidden = shown>0;
  }
  ['input','change'].forEach(function(ev){
    document.addEventListener(ev, function(e){
      if(!e.target.classList || !(e.target.classList.contains('sx-q') || e.target.classList.contains('sx-d'))) return;
      filterSpecs(e.target.closest('dialog'));
    });
  });
  document.addEventListener('click', function(e){
    var a = e.target.closest && e.target.closest('.sx-chip'); if(!a) return;
    e.preventDefault();
    var dlg = a.closest('dialog'), t = dlg.querySelector(a.getAttribute('href').replace(/([^\w#-])/g,'\\$1'));
    if(!t || t.hidden){ var q = dlg.querySelector('.sx-q'); if(q){ q.value = ''; } var dd = dlg.querySelector('.sx-d'); if(dd) dd.checked = false; filterSpecs(dlg); t = dlg.querySelector(a.getAttribute('href').replace(/([^\w#-])/g,'\\$1')); }
    if(t) t.scrollIntoView({block:'start', behavior:reduced?'auto':'smooth'});
  });
  /* پاپ‌آپ «مشخصات کامل» یک محصول */
  var specDlg = $('#specDlg');
  function openSpecs(cat, pid){
    var p = prodOf(cat, pid); if(!p) return;
    var groups = fullSpecs(p), cols = prodColorsAll(p, cat);
    $('#specTitle').textContent = 'مشخصات کامل';
    $('#specBody').innerHTML =
      '<div class="sx-prod"><span class="sx-img">'+NQ.art(p.kind, cols[0] ? COLORS[cols[0]] : null)+'</span><div class="sx-pi"><b>'+esc(p.title)+'</b>'+(p.tagline?'<small>'+esc(p.tagline)+'</small>':'')+'</div>'+torobBtn(p)+'</div>' +
      specTools(groups.map(function(g){return g.g}), false) +
      '<div class="sx-list">' + groups.map(function(g){
        return '<section class="sx-group"><h3 class="sx-head" id="sxg-'+slug(g.g)+'">'+esc(g.g)+' <small>('+fa(g.items.length)+')</small></h3>' +
          g.items.map(function(it){ return '<div class="sx-row" data-t="'+esc(nw(it[0]+' '+it[1]))+'"><span class="sx-k">'+esc(it[0])+'</span><span class="sx-v">'+esc(it[1])+'</span></div>'; }).join('') + '</section>';
      }).join('') + '<p class="sx-empty" hidden>موردی با این جستجو پیدا نشد.</p></div>' +
      '<p class="sp-note">مشخصات نمونه است و فقط برای نمایش آورده شده.</p>';
    if(typeof specDlg.showModal==='function') specDlg.showModal(); else specDlg.setAttribute('open','');
    specDlg.querySelector('.sx-scroll').scrollTop = 0;
  }
  $('#specClose').addEventListener('click', function(){ specDlg.close(); });
  specDlg.addEventListener('click', function(e){ if(e.target===specDlg) specDlg.close(); });
  document.addEventListener('click', function(e){
    var b = e.target.closest && e.target.closest('[data-specs]'); if(!b) return;
    openSpecs(b.getAttribute('data-sc'), b.getAttribute('data-specs'));
  });
  var cmpDlg = $('#cmpDlg');
  function openFullCmp(){
    var prods = state.pcmp.map(prodById).filter(Boolean);
    if(prods.length<2) return;
    $('#cmpDlgTitle').textContent = 'مقایسهٔ کامل '+fa(prods.length)+' محصول';
    $('#cmpDlgBody').innerHTML = fullCmpHTML(prods);
    if(typeof cmpDlg.showModal==='function') cmpDlg.showModal(); else cmpDlg.setAttribute('open','');
    $('#cmpDlgBody').scrollTop = 0;
  }
  $('#cmpDlgClose').addEventListener('click', function(){ cmpDlg.close(); });
  cmpDlg.addEventListener('click', function(e){ if(e.target===cmpDlg) cmpDlg.close(); });
  function togglePCmp(id){
    var c = state.pcmp, i = c.indexOf(id);
    if(i>-1) c.splice(i, 1);
    else if(c.length>=MAX_CMP){ toast('حداکثر '+fa(MAX_CMP)+' محصول را می‌شود با هم مقایسه کرد؛ یکی را بردارید.', 'warn'); return; }
    else c.push(id);
    renderAll();
    if(c.length===2 && i<0) listTop(true);
  }
  function togglePInfo(id){
    if(state.pinfo[id]) delete state.pinfo[id]; else state.pinfo[id] = true;
    renderProducts();
  }
  /* «مشاهده در ترب»: صفحهٔ محصول در ترب (جستجوی نام محصول) در صفحهٔ جدید */
  function torobBtn(p){ return '<a class="torob-btn" href="https://torob.com/search/?query='+encodeURIComponent(p.title)+'" target="_blank" rel="noopener">مشاهده در ترب'+IC.ext+'</a>'; }
  function specsDL(list, cls){ return '<dl class="specs'+(cls?' '+cls:'')+'">'+list.map(function(r){return '<div><dt>'+esc(r[0])+'</dt><dd>'+esc(r[1])+'</dd></div>'}).join('')+'</dl>'; }
  /* مشخصات کامل گروه‌بندی‌شده: full اگر باشد؛ وگرنه کلیدی + بیشتر */
  function fullSpecs(p){
    if(p.full && p.full.length) return p.full;
    var g = [];
    if((p.specs||[]).length) g.push({g:'مشخصات کلیدی', items:p.specs});
    if((p.more||[]).length) g.push({g:'مشخصات بیشتر', items:p.more});
    return g;
  }
  function specCount(p){ return fullSpecs(p).reduce(function(a,g){return a+g.items.length}, 0); }
  /* دکمهٔ «مشخصات کامل» (پاپ‌آپ) */
  function fullSpecsBtn(p, cat){
    var n = specCount(p), k = (p.specs||[]).length;
    if(n<=k) return '';
    return '<button type="button" class="sp-moreb" data-specs="'+p.id+'" data-sc="'+(cat||state.cat)+'" aria-haspopup="dialog">مشخصات کامل <small>('+fa(n)+' مورد)</small>'+IC.expand+'</button>';
  }
  /* جزئیات محصول: مشخصات کلیدی + دکمهٔ «مشخصات کامل» که پاپ‌آپ باز می‌کند */
  function infoHTML(p,s){
    var cols = s.colors.map(function(c){return '<li><i class="sw" style="background:'+COLORS[c]+'"></i>'+c+'</li>'}).join('');
    return (p.desc ? '<p class="sp-desc">'+esc(p.desc)+'</p>' : '') +
      ((p.specs||[]).length ? '<h4 class="sp-h">مشخصات کلیدی</h4>'+specsDL(p.specs) : '') +
      fullSpecsBtn(p) +
      (cols ? '<div class="sp-colors"><span>رنگ‌های موجود</span><ul>'+cols+'</ul></div>' : '') +
      '<p class="sp-note">مشخصات نمونه است و فقط برای نمایش آورده شده.</p>';
  }
  function renderPickBar(){
    var p = curProd();
    if(state.tab==='plan' || stage()!=='stores' || !p){
      pickBarEl.hidden = true;
      if(lastBar){pickBarEl.innerHTML = ''; lastBar = ''}
      return;
    }
    var s = prodStats(p), open = state.info;
    var ctx = 'bar:'+p.id, gx = state.gx && state.gx.key===ctx;
    var html = '<section class="sp'+(gx?' gx':'')+'" tabindex="-1" aria-label="محصول انتخاب‌شده: '+esc(p.title)+'">' + gviewHTML(ctx) +
      '<div class="sp-main">'+thumbHTML('sp-img', p, state.cat, ctx, artHTML(p,s)) +
        '<div class="sp-info"><span class="sp-name" data-full="'+esc(p.title)+'">'+esc(p.title)+'</span>' +
          '<span class="sp-sub">'+swatches(s.colors)+'<span>'+fa(s.n)+' فروشگاه</span>'+(s.min ? '<span>از <b>'+fa(s.min)+'</b> تومان</span>' : '')+'</span></div>' +
        (prodsOf(state.cat).length>1 ? '<button type="button" class="cmp-ic" id="spCmp" aria-label="مقایسه با محصول دیگر" title="مقایسه با محصول دیگر">'+ICON.cmp+'</button>' : '') +
        '<button type="button" class="sp-change" id="spChange">تغییر محصول</button></div>' +
      '<button type="button" class="sp-more" id="spMore" aria-expanded="'+open+'" aria-controls="spPanel"><span>مشاهدهٔ جزئیات</span>'+CHEV_DOWN+'</button>' +
      '<div class="sp-panel" id="spPanel"'+(open ? '' : ' hidden')+'>'+infoHTML(p,s)+torobBtn(p)+'</div></section>';
    pickBarEl.hidden = false;
    if(html!==lastBar){pickBarEl.innerHTML = html; lastBar = html}
  }
  /* کل ستون فهرست با هم اسکرول می‌شود (سربرگ محصول و کارت‌ها) */
  function listTop(smooth){ $('#list').scrollTo({top:0, behavior: smooth && !reduced ? 'smooth' : 'auto'}); }
  function bump(el){el.classList.add('enter'); clearTimeout(el._t); el._t = setTimeout(function(){el.classList.remove('enter')},900)}
  function selectProduct(id, sid){
    if(!prodById(id)) return;
    state.product = id; state.info = false; state.picks = {A:null,B:null}; state.selected = null;
    if(sid){ if(state.compare) state.picks.A = sid; else state.selected = sid; }
    bump(cardsEl);
    if(isMobile()){ setTopMin(true); setSheet('half', !!sid); }
    renderAll(); fitResults();
    listTop(false);
    if(sid){
      revealStore(sid);
      requestAnimationFrame(function(){
        var el = cardsEl.querySelector('.card[data-sid="'+sid+'"]');
        if(el) el.scrollIntoView({block:isMobile() ? 'start' : 'nearest',behavior:reduced||isMobile()?'auto':'smooth'});
      });
    } else {
      var sp = pickBarEl.querySelector('.sp'); if(sp) sp.focus({preventScroll:true});
    }
  }
  function clearProduct(){
    state.product = null; state.info = false; state.picks = {A:null,B:null}; state.selected = null;
    bump(prodsEl);
    setSheet('full'); listEl.scrollTop = 0;
    renderAll(); fitResults();
    listTop(false);
    var b = prodsEl.querySelector('.prod-main'); if(b) b.focus({preventScroll:true});
  }
  function compareFromBar(){
    var id = state.product; if(!id) return;
    if(state.pcmp.indexOf(id)<0 && state.pcmp.length<MAX_CMP) state.pcmp.push(id);
    clearProduct();
  }
  function toggleInfo(){
    state.info = !state.info;
    renderPickBar();
    var b = $('#spMore'); if(b) b.focus({preventScroll:true});
  }
  function pickFromPin(sid){
    var o = offerRows().filter(function(x){return x.sid===sid})[0], p = o && prodByTitle(o.title);
    if(p) selectProduct(p.id, sid);
  }

  /* ---------- روش رفت‌وآمد ---------- */
  var tBtn = $('#tBtn'), tPop = $('#tPop');
  var lastTravel = '';
  /* دکمه و گزینه‌های منوی روش رفت‌وآمد (نوار بالای فهرست و پاپ‌آپ فیلتر از یک منو استفاده می‌کنند) */
  function travelBtnHTML(cur){
    return IC[cur]+'<span>'+Travel.label(cur)+'</span><svg class="tdrop-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
  }
  function travelOptsHTML(cur){
    return Travel.MENU.map(function(id){
      return '<li role="option" tabindex="-1" class="topt'+(id===cur?' cur':'')+'" data-travel="'+id+'" aria-selected="'+(id===cur)+'">'+IC[id]+
        '<span class="topt-t"><b>'+Travel.label(id)+'</b></span>'+
        (id===cur?'<svg class="topt-ck" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>':'')+'</li>';
    }).join('');
  }
  /* کلیدهای جهت‌نما، Enter، Esc و Tab داخل منو */
  function popKeys(e, pop, close){
    var items = Array.prototype.slice.call(pop.children), i = items.indexOf(document.activeElement);
    if(e.key==='ArrowDown'){e.preventDefault(); items[(i+1)%items.length].focus()}
    else if(e.key==='ArrowUp'){e.preventDefault(); items[(i-1+items.length)%items.length].focus()}
    else if(e.key==='Enter'||e.key===' '){e.preventDefault(); if(i>-1) items[i].click()}
    else if(e.key==='Escape'){e.preventDefault(); e.stopPropagation(); close(true)}
    else if(e.key==='Tab') close(false);
  }
  function renderTravel(){
    var cur = Travel.mode;
    tBtn.innerHTML = travelBtnHTML(cur);
    var html = travelOptsHTML(cur);
    if(html!==lastTravel){tPop.innerHTML = html; lastTravel = html}
  }
  function openTravel(){ tPop.hidden = false; tBtn.setAttribute('aria-expanded','true'); var c = tPop.querySelector('.cur')||tPop.firstElementChild; if(c) c.focus(); }
  function closeTravel(focusBtn){ if(tPop.hidden) return; tPop.hidden = true; tBtn.setAttribute('aria-expanded','false'); if(focusBtn) tBtn.focus(); }
  tBtn.addEventListener('click',function(){ tPop.hidden ? openTravel() : closeTravel(true) });
  tBtn.addEventListener('keydown',function(e){ if(e.key==='ArrowDown'&&tPop.hidden){e.preventDefault(); openTravel()} });
  tPop.addEventListener('click',function(e){
    var o = e.target.closest('[data-travel]'); if(!o) return;
    Travel.set(o.getAttribute('data-travel')); closeTravel(true); afterFilterChange();
  });
  tPop.addEventListener('keydown',function(e){ popKeys(e, tPop, closeTravel); });
  document.addEventListener('click',function(e){ if(!tPop.hidden && !e.target.closest('#tdrop')) closeTravel(false) });

  /* ---------- فیلتر (پاپ‌آپ) ---------- */
  var STOCK_SHORT = {in:'موجود و بروز', unsure:'تأییدنشده', out:'ناموجود'};
  var TIMES = [0,5,10,15,30,45];
  var STEP = 10000;
  var dlg = $('#filterDlg'), fBody = $('#fBody');
  $('#filterIc').innerHTML = IC.filter;
  $('#zclu').innerHTML = IC.group;

  function filterChips(){
    var f = state.filters, out = [];
    var on = ['in','unsure','out'].filter(function(k){return f.stock[k]});
    if(on.length<3) out.push({k:'stock', t:'موجودی: '+on.map(function(k){return STOCK_SHORT[k]}).join('، ')});
    if(f.pmin!=null || f.pmax!=null) out.push({k:'price', t:'قیمت '+(f.pmin!=null?'از '+fa(Math.round(f.pmin/1000))+' ':'')+(f.pmax!=null?'تا '+fa(Math.round(f.pmax/1000)):'')+(f.pmax==null?'':'')+' هزار'});
    if(f.brands.length) out.push({k:'brands', t:'برند: '+f.brands.join('، ')});
    if(f.colors.length) out.push({k:'colors', t:'رنگ: '+f.colors.join('، ')});
    if(f.maxMin) out.push({k:'time', t:'تا '+fa(f.maxMin)+' دقیقه'});
    if(f.torobpay) out.push({k:'torobpay', t:'ترب‌پی', ic:IC.torobpay});
    if(f.installment) out.push({k:'installment', t:'قسطی', ic:IC.installment});
    if(f.openNow) out.push({k:'openNow', t:'الان باز است'});
    if(f.warranty) out.push({k:'warranty', t:'دارای گارانتی'});
    if(f.kalabarg) out.push({k:'kalabarg', t:'پوشش کالابرگ', ic:IC.kalabarg});
    if(f.fast) out.push({k:'fast', t:'ارسال فوری', ic:IC.truck});
    if(f.guarantee) out.push({k:'guarantee', t:'ضمانت ترب'});
    if(f.minRate) out.push({k:'minRate', t:'امتیاز '+fa1(f.minRate)+' به بالا', ic:IC.star});
    if(f.maxKm) out.push({k:'maxKm', t:'تا '+fa(f.maxKm)+' کیلومتر'});
    if(f.area) out.push({k:'area', t:'محدودهٔ انتخابی روی نقشه'});
    if(f.near) out.push({k:'near', t:'منطقه: '+f.near.label, ic:IC.pin});
    return out;
  }
  function activeFilterCount(){return filterChips().length}
  function clearFilterKey(k){
    var f = state.filters, d = defFilters();
    if(k==='stock') f.stock = d.stock;
    else if(k==='price'){f.pmin = null; f.pmax = null}
    else if(k==='colors') f.colors = [];
    else if(k==='brands') f.brands = [];
    else if(k==='time') f.maxMin = 0;
    else if(k==='minRate' || k==='maxKm') f[k] = 0;
    else if(k==='area') f.area = null;
    else if(k==='near') f.near = null;
    else f[k] = false;
  }
  var lastChips = '';
  function renderFilterUI(){
    var chips = filterChips(), n = chips.length;
    var c = $('#fCount'); c.hidden = !n; c.textContent = fa(n);
    $('#filterBtn').classList.toggle('on', n>0);
    var html = chips.map(function(x){
      return '<span class="fchip">'+(x.ic||'')+'<span>'+esc(x.t)+'</span><button type="button" data-fclear="'+x.k+'" aria-label="حذف فیلتر: '+esc(x.t)+'">×</button></span>';
    }).join('');
    if(html!==lastChips){$('#fChips').innerHTML = html; lastChips = html}
  }
  function priceBounds(){
    var r = rawRows(); if(!r.length) return {lo:0,hi:STEP};
    var ps = r.map(function(o){return o.price});
    var lo = Math.floor(Math.min.apply(null,ps)/STEP)*STEP, hi = Math.ceil(Math.max.apply(null,ps)/STEP)*STEP;
    if(hi-lo<STEP*2) hi = lo+STEP*2;
    return {lo:lo,hi:hi};
  }
  function chip(attr,val,on,html){
    return '<button type="button" class="fc'+(on?' on':'')+'" data-'+attr+'="'+val+'" aria-pressed="'+on+'">'+html+'</button>';
  }
  function filterBodyHTML(){
    var f = state.filters, b = priceBounds();
    var lo = f.pmin==null ? b.lo : Math.max(b.lo,f.pmin), hi = f.pmax==null ? b.hi : Math.min(b.hi,f.pmax);
    var colors = [], brands = []; rawRows().forEach(function(o){o.colors.forEach(function(c){if(colors.indexOf(c)<0) colors.push(c)}); if(o.brand && brands.indexOf(o.brand)<0) brands.push(o.brand)});
    var h = '';
    h += '<section class="fs"><h3>موجودی</h3><div class="fcs">'+['in','unsure','out'].map(function(k){
      return chip('fstock',k,f.stock[k],'<span class="stock '+k+'">'+STOCK[k]+'</span>');
    }).join('')+'</div></section>';
    h += '<section class="fs"><h3>محدودهٔ قیمت <small>(تومان)</small></h3>' +
      '<div class="rng" id="rng"><div class="rng-track"><i class="rng-fill" id="rngFill"></i></div>' +
      '<input type="range" id="fpmin" aria-label="حداقل قیمت" min="'+b.lo+'" max="'+b.hi+'" step="'+STEP+'" value="'+lo+'">' +
      '<input type="range" id="fpmax" aria-label="حداکثر قیمت" min="'+b.lo+'" max="'+b.hi+'" step="'+STEP+'" value="'+hi+'"></div>' +
      '<div class="rng-vals"><span>از <b id="fpminL"></b></span><span>تا <b id="fpmaxL"></b></span></div></section>';
    if(brands.length>1) h += '<section class="fs"><h3>برند</h3><div class="fcs">'+brands.map(function(b){
      return chip('fbrand',b,f.brands.indexOf(b)>-1,'<span class="fc-brand">'+esc(b)+'</span>');
    }).join('')+'</div></section>';
    if(colors.length>1) h += '<section class="fs"><h3>رنگ</h3><div class="fcs">'+colors.map(function(c){
      return chip('fcolor',c,f.colors.indexOf(c)>-1,'<i class="sw" style="background:'+COLORS[c]+'"></i>'+c);
    }).join('')+'</div></section>';
    h += '<section class="fs"><h3>زمان رسیدن</h3>' +
      '<div class="fsel-row"><span id="ftLbl">روش رفت‌وآمد</span><div class="tdrop ftdrop" id="ftdrop">' +
        '<button type="button" class="tdrop-btn" id="ftBtn" aria-haspopup="listbox" aria-expanded="false" aria-controls="ftPop" aria-labelledby="ftLbl ftBtn">'+travelBtnHTML(Travel.mode)+'</button>' +
        '<ul class="tdrop-pop" id="ftPop" role="listbox" aria-label="روش رفت‌وآمد" hidden>'+travelOptsHTML(Travel.mode)+'</ul></div></div>' +
      '<div class="fcs">'+TIMES.map(function(t){
      return chip('ftime',t,f.maxMin===t,t?'تا '+fa(t)+' دقیقه':'همه');
    }).join('')+'</div></section>';
    h += '<section class="fs"><h3>پرداخت</h3>' +
      '<label class="frow"><input type="checkbox" data-fflag="torobpay"'+(f.torobpay?' checked':'')+'><span class="frow-t">'+IC.torobpay+'پرداخت با ترب‌پی فعال باشد</span></label>' +
      '<label class="frow"><input type="checkbox" data-fflag="installment"'+(f.installment?' checked':'')+'><span class="frow-t">'+IC.installment+'امکان پرداخت قسطی</span></label></section>';
    /* فیلترهای وابسته به دسته: خوراکی ← کالابرگ؛ بقیه ← گارانتی */
    if(isFood()) h += '<section class="fs"><h3>کالابرگ</h3>' +
      '<label class="frow"><input type="checkbox" data-fflag="kalabarg"'+(f.kalabarg?' checked':'')+'><span class="frow-t">'+IC.kalabarg+'فقط کالاهایی که پوشش کالابرگ دارند</span></label></section>';
    else h += '<section class="fs"><h3>گارانتی</h3>' +
      '<label class="frow"><input type="checkbox" data-fflag="warranty"'+(f.warranty?' checked':'')+'><span class="frow-t">فقط کالاهای دارای گارانتی</span></label></section>';
    h += '<section class="fs"><h3>فروشگاه</h3><div class="fcs">'+[0,3.5,4,4.5].map(function(r){
      return chip('frate',r,f.minRate===r,r?IC.star+'امتیاز '+fa1(r)+'+':'همهٔ امتیازها');
    }).join('')+'</div>' +
      '<label class="frow"><input type="checkbox" data-fflag="guarantee"'+(f.guarantee?' checked':'')+'><span class="frow-t">فقط فروشگاه‌های دارای ضمانت ترب</span></label>' +
      '<label class="frow"><input type="checkbox" data-fflag="fast"'+(f.fast?' checked':'')+'><span class="frow-t">'+IC.truck+'ارسال فوری</span></label></section>';
    h += '<section class="fs"><h3>محدودهٔ جستجو</h3><div class="fcs">'+[0,1,2,5,10].map(function(k){
      return chip('fkm',k,f.maxKm===k,k?'تا '+fa(k)+' کیلومتر از من':'همه‌جا');
    }).join('')+'</div>' +
      '<label class="frow"><input type="checkbox" data-farea'+(f.area?' checked':'')+'><span class="frow-t">فقط فروشگاه‌های داخل محدودهٔ فعلی نقشه</span></label></section>';
    h += '<section class="fs"><h3>ساعت کار</h3>' +
      '<label class="frow"><input type="checkbox" data-fflag="openNow"'+(f.openNow?' checked':'')+'><span class="frow-t">فقط فروشگاه‌هایی که همین الان باز هستند</span></label></section>';
    return h;
  }
  function syncRange(){
    var a = $('#fpmin'), z = $('#fpmax'); if(!a||!z) return;
    var mn = +a.min, mx = +a.max, span = (mx-mn)||1;
    $('#rng').style.setProperty('--lo', ((+a.value-mn)/span*100)+'%');
    $('#rng').style.setProperty('--hi', ((+z.value-mn)/span*100)+'%');
    $('#fpminL').textContent = fa(+a.value);
    $('#fpmaxL').textContent = fa(+z.value);
  }
  function syncFilterFoot(){
    var n = stage()==='pick' ? pickList().length : offerRows().length;
    $('#fDone').textContent = 'نمایش '+fa(n)+(stage()==='pick'?' محصول':' فروشگاه');
    $('#fReset').hidden = !activeFilterCount();
  }
  function afterFilterChange(){
    var ok = {}; offerRows().forEach(function(o){ok[o.sid]=1});
    if(state.selected && !ok[state.selected]) state.selected = null;
    ['A','B'].forEach(function(k){ if(state.picks[k] && !ok[state.picks[k]]) state.picks[k] = null });
    renderAll();
    if(dlg.open) syncFilterFoot();
  }
  function openFilter(){
    if(!state.cat){toast('اول یک محصول جستجو کنید.','info'); return}
    $('#fTitle').textContent = stage()==='pick' ? 'فیلتر محصولات' : 'فیلتر فروشگاه‌ها';
    fBody.innerHTML = filterBodyHTML(); syncRange(); syncFilterFoot();
    if(typeof dlg.showModal==='function') dlg.showModal(); else dlg.setAttribute('open','');
  }
  $('#filterBtn').addEventListener('click',openFilter);
  $('#fClose').addEventListener('click',function(){dlg.close()});
  $('#fDone').addEventListener('click',function(){dlg.close()});
  dlg.addEventListener('click',function(e){ if(e.target===dlg) dlg.close() });
  $('#fReset').addEventListener('click',function(){
    state.filters = defFilters(); fBody.innerHTML = filterBodyHTML(); syncRange(); afterFilterChange();
  });
  /* منوی روش رفت‌وآمد داخل فیلتر (همان منوی سفارشی نوار بالا، نه select مرورگر) */
  function openFTravel(){
    var p = $('#ftPop'); if(!p) return;
    p.hidden = false; $('#ftBtn').setAttribute('aria-expanded','true');
    /* اگر پایینِ بخش فیلتر جا نیست، منو رو به بالا باز شود */
    var br = $('#ftBtn').getBoundingClientRect(), fr = fBody.getBoundingClientRect();
    p.classList.toggle('up', br.bottom + p.offsetHeight + 8 > fr.bottom && br.top - p.offsetHeight - 8 > fr.top);
    var c = p.querySelector('.cur')||p.firstElementChild; if(c) c.focus({preventScroll:true});
  }
  function closeFTravel(focusBtn){ var p = $('#ftPop'); if(!p || p.hidden) return; p.hidden = true; $('#ftBtn').setAttribute('aria-expanded','false'); if(focusBtn) $('#ftBtn').focus(); }
  fBody.addEventListener('keydown',function(e){
    if(e.target.id==='ftBtn' && e.key==='ArrowDown' && $('#ftPop').hidden){ e.preventDefault(); openFTravel(); return; }
    if(e.target.closest('#ftPop')) popKeys(e, $('#ftPop'), closeFTravel);
  });
  dlg.addEventListener('click',function(e){ if(!e.target.closest('#ftdrop')) closeFTravel(false); });
  dlg.addEventListener('cancel',function(e){ var p = $('#ftPop'); if(p && !p.hidden){ e.preventDefault(); closeFTravel(true); } });
  fBody.addEventListener('click',function(e){
    var o = e.target.closest('[data-travel]');
    if(o){
      Travel.set(o.getAttribute('data-travel'));
      $('#ftBtn').innerHTML = travelBtnHTML(Travel.mode); $('#ftPop').innerHTML = travelOptsHTML(Travel.mode);
      closeFTravel(true); afterFilterChange(); return;
    }
    if(e.target.closest('#ftBtn')){ $('#ftPop').hidden ? openFTravel() : closeFTravel(true); return; }
    var b = e.target.closest('button'); if(!b) return;
    var f = state.filters, k;
    if((k = b.getAttribute('data-fstock'))){
      var next = !f.stock[k];
      if(!next && !['in','unsure','out'].some(function(x){return x!==k && f.stock[x]})) return;   // حداقل یک گزینه
      f.stock[k] = next; b.classList.toggle('on',next); b.setAttribute('aria-pressed',String(next));
    } else if((k = b.getAttribute('data-fbrand'))){
      var bi = f.brands.indexOf(k); if(bi>-1) f.brands.splice(bi,1); else f.brands.push(k);
      var bon = bi<0; b.classList.toggle('on',bon); b.setAttribute('aria-pressed',String(bon));
    } else if((k = b.getAttribute('data-fcolor'))){
      var i = f.colors.indexOf(k); if(i>-1) f.colors.splice(i,1); else f.colors.push(k);
      var on = i<0; b.classList.toggle('on',on); b.setAttribute('aria-pressed',String(on));
    } else if(b.hasAttribute('data-frate') || b.hasAttribute('data-fkm')){
      var ak = b.hasAttribute('data-frate') ? 'data-frate' : 'data-fkm', fk = ak==='data-frate' ? 'minRate' : 'maxKm';
      f[fk] = +b.getAttribute(ak);
      Array.prototype.forEach.call(fBody.querySelectorAll('['+ak+']'),function(x){
        var on3 = +x.getAttribute(ak)===f[fk]; x.classList.toggle('on',on3); x.setAttribute('aria-pressed',String(on3));
      });
    } else if(b.hasAttribute('data-ftime')){
      f.maxMin = +b.getAttribute('data-ftime');
      Array.prototype.forEach.call(fBody.querySelectorAll('[data-ftime]'),function(x){
        var on2 = +x.getAttribute('data-ftime')===f.maxMin; x.classList.toggle('on',on2); x.setAttribute('aria-pressed',String(on2));
      });
    } else return;
    afterFilterChange();
  });
  fBody.addEventListener('change',function(e){
    if(e.target.hasAttribute('data-farea')){ state.filters.area = e.target.checked ? MapView.getBounds() : null; afterFilterChange(); return; }
    var k = e.target.getAttribute('data-fflag'); if(!k) return;
    state.filters[k] = e.target.checked; afterFilterChange();
  });
  fBody.addEventListener('input',function(e){
    var a = $('#fpmin'), z = $('#fpmax');
    if(e.target!==a && e.target!==z) return;
    if(e.target===a && +a.value>+z.value-STEP) a.value = +z.value-STEP;
    if(e.target===z && +z.value<+a.value+STEP) z.value = +a.value+STEP;
    var bd = priceBounds();
    state.filters.pmin = +a.value<=bd.lo ? null : +a.value;
    state.filters.pmax = +z.value>=bd.hi ? null : +z.value;
    syncRange(); afterFilterChange();
  });
  $('#fChips').addEventListener('click',function(e){
    var b = e.target.closest('[data-fclear]'); if(!b) return;
    clearFilterKey(b.getAttribute('data-fclear')); afterFilterChange();
  });
  document.addEventListener('click',function(e){
    if(!e.target.closest('[data-act="clearf"]')) return;
    state.filters = defFilters(); afterFilterChange();
  });

  function renderAll() {
    var rows = visibleRows();
    renderTabs(); renderTravel();
    renderChips(); renderControls(); renderSummary(rows); renderCmp(); renderList(rows); renderPCmp(); renderProducts(); renderPickBar();
    renderPlan(); renderPlanCmp();
    if (state.tab === 'plan') renderPlanMap(); else { renderPins(rows); renderRoutes(); }
    MapView.setOrigin(state.origin);
    MapView.setArea(state.tab === 'results' && state.cat ? state.filters.area : null);
    var nearC = state.tab === 'results' ? (state.cat ? state.filters.near : state.dir && state.dir.near) : null;
    MapView.setCircle(nearC);
    var pill = $('#areaPill');
    pill.hidden = !nearC;
    if (nearC) pill.innerHTML = IC.pin + '<span>' + esc(nearC.label) + '</span><button type="button" data-act="' + (state.cat ? 'clearnear' : 'cleardir') + '" aria-label="پاک کردن منطقه">×</button>';
    if (state.tab !== 'results' || stage() === 'none') areaBtn.hidden = true;
    renderSearchSel(); renderPeek();
    if (NQ.AgentUI && NQ.AgentUI.sync) NQ.AgentUI.sync();   // پنل «سر زدن‌ها»ی تربچت
    syncGview();
  }
  var raf = 0;
  function scheduleRender() { if (raf) return; raf = requestAnimationFrame(function () { raf = 0; renderAll(); }); }

  /* ---------- فروشگاه‌ها بدون محصول: نوع فروشگاه، مناطق، پرتراکم‌ترین محدوده ---------- */
  var KIND_NAME = {digital:'لوازم دیجیتال', food:'مواد غذایی', all:''};
  function storeKinds(sid){
    var k = {};
    Object.keys(OFFERS).forEach(function(cat){ if(OFFERS[cat].some(function(r){return r[0]===sid})) k[isFood(cat) ? 'food' : 'digital'] = 1; });
    return k;
  }
  function storeKind(sid){ var k = storeKinds(sid); return k.digital || !k.food ? 'digital' : 'food'; }
  function storeArtHTML(sid){ return NQ.storeArt(sid, storeKind(sid)); }
  function inCircle(p, c){ return NQ.geo.distanceKm(p, c) <= c.r; }
  /* چهار نقطهٔ دور دایره (برای جاگیری نقشه) */
  function circlePts(c){
    if(!c) return [];
    var dLat = c.r/111, dLng = c.r/(111*Math.cos(c.lat*Math.PI/180));
    return [{lat:c.lat+dLat,lng:c.lng},{lat:c.lat-dLat,lng:c.lng},{lat:c.lat,lng:c.lng+dLng},{lat:c.lat,lng:c.lng-dLng}];
  }
  function sellsIn(sid, cat){ return (OFFERS[cat]||[]).some(function(r){return r[0]===sid && r[4]!=='out'}); }
  /* فروشگاه‌ها با شرط: cat (کالا را موجود دارد)، kind (digital | food | all)، near (داخل دایره)؛ نزدیک‌ترین اول */
  function storesWhere(q){
    return Object.keys(STORES).filter(function(sid){
      return (!q.cat || sellsIn(sid, q.cat)) && (!q.kind || q.kind==='all' || storeKinds(sid)[q.kind]) && (!q.near || inCircle(STORES[sid], q.near));
    }).sort(function(a,b){ return roadKm(state.origin, STORES[a]) - roadKm(state.origin, STORES[b]); });
  }
  function dirRows(){ return state.dir ? (state.dir.sids || storesWhere(state.dir)) : []; }
  /* پرتراکم‌ترین محدوده: دایره‌ای به شعاع r (مرکز = یکی از فروشگاه‌ها) که بیشترین فروشگاه را دارد؛ بعد مرکز به میانگین آنها می‌رود */
  function hotspot(sids, r){
    var best = null;
    sids.forEach(function(a){
      var inn = sids.filter(function(b){ return NQ.geo.distanceKm(STORES[a], STORES[b]) <= r; });
      var spread = inn.reduce(function(t,b){ return t + NQ.geo.distanceKm(STORES[a], STORES[b]); }, 0);
      if(!best || inn.length>best.inn.length || (inn.length===best.inn.length && spread<best.spread)) best = {a:a, inn:inn, spread:spread};
    });
    if(!best) return null;
    var lat = 0, lng = 0;
    best.inn.forEach(function(b){ lat += STORES[b].lat; lng += STORES[b].lng; });
    var c = {lat: lat/best.inn.length, lng: lng/best.inn.length, r: r};
    var inside = sids.filter(function(b){ return inCircle(STORES[b], c); });
    if(inside.length < best.inn.length){ c = {lat: STORES[best.a].lat, lng: STORES[best.a].lng, r: r}; inside = best.inn; }
    c.anchor = best.a;
    return {c: c, sids: inside};
  }
  function areaLabel(c){
    var near = (NQ.AREAS||[]).filter(function(a){ return NQ.geo.distanceKm(a, c) <= a.r + .3; })
      .sort(function(x,y){ return NQ.geo.distanceKm(x, c) - NQ.geo.distanceKm(y, c); })[0];
    return 'اطراف ' + (near ? near.name : STORES[c.anchor].name);
  }
  /* پرسش منطقه (از تربچت یا دکمه‌ها): {cat, kind, place: 'me' | شناسهٔ محله | null, hotspot, r} */
  function areaQuery(q){
    q = q || {};
    var near = null, label = '';
    if(q.place==='me'){ near = {lat: state.origin.lat, lng: state.origin.lng, r: q.r || 1.5}; label = 'اطراف شما'; }
    else if(q.place){ var A = (NQ.AREAS||[]).filter(function(a){return a.id===q.place})[0]; if(A){ near = {lat: A.lat, lng: A.lng, r: q.r || A.r}; label = A.name; } }
    var sids = storesWhere({cat: q.cat, kind: q.kind, near: q.hotspot ? null : near});
    if(q.hotspot){
      var base = near ? sids.filter(function(s){ return inCircle(STORES[s], near); }) : sids;
      var hs = hotspot(base, q.r || 1);
      if(hs){ near = {lat: hs.c.lat, lng: hs.c.lng, r: hs.c.r}; label = areaLabel(hs.c); sids = hs.sids; }
      else sids = [];
    }
    if(near) near.label = label + ' (' + fa1(near.r) + ' کیلومتر)';
    return {q: q, label: label, near: near, sids: sids, cat: q.cat || null, kind: q.kind || 'all', hotspot: !!q.hotspot,
            dist: near ? roadKm(state.origin, near) : 0, origin: {lat: state.origin.lat, lng: state.origin.lng},
            stores: sids.map(storeInfo)};
  }
  function storeInfo(sid){
    var st = STORES[sid], km = roadKm(state.origin, st), x = storeStatus(st);
    return {sid: sid, name: st.name, art: storeArtHTML(sid), rating: st.rating || 0, years: st.years || 0, guarantee: !!st.guarantee, torobpay: !!st.torobpay,
            fast: st.fast || '', status: x.short, statusK: x.k, km: km, eta: etaHTML(km, sid), addr: st.addr, lat: st.lat, lng: st.lng, kind: KIND_NAME[storeKind(sid)]};
  }
  /* نمایش یک منطقه در صفحهٔ فهرست یا نقشه: با کالا ← فیلتر منطقه روی همان کالا؛ بدون کالا ← فهرست فروشگاه‌های منطقه */
  function showArea(a, to){
    state.tab = 'results'; state.selected = null; state.compare = false;
    if(a.cat){
      if(state.cat!==a.cat){ qEl.value = (catById(a.cat)||{}).name || ''; setCat(a.cat); }
      state.filters.near = a.near;
    } else {
      if(state.cat || state.dir){ qEl.value = ''; setCat(null); }
      state.dir = {label: a.near ? a.near.label : 'همهٔ فروشگاه‌ها', kind: a.kind, near: a.near, sids: a.sids};
    }
    if(view!==to) goView(to, {noFit: true});
    if(to==='map') setSheet('half');
    renderAll(); fitResults(); listTop(false);
  }
  /* یک فروشگاه روی نقشه (از کارت فروشنده): اگر کالای فعلی را ندارد، جستجو پاک می‌شود */
  function storeOnMap(sid){
    if(state.cat && !(OFFERS[state.cat]||[]).some(function(r){return r[0]===sid})){ qEl.value = ''; setCat(null); }
    if(state.dir && dirRows().indexOf(sid)<0) state.dir = null;
    state.tab = 'results'; state.compare = false; state.selected = sid;
    goView('map', {noFit: true}); setSheet('peek'); renderAll(); revealStore(sid);
  }
  /* کارت فروشگاه در فهرست (منطقه / بدون کالا): مثل کارت نتایج، با عکس فروشگاه به‌جای قیمت */
  function dirCardHTML(sid, i){
    var st = STORES[sid], km = roadKm(state.origin, st), sel = state.selected===sid, infoOpen = sel || !!state.sinfo[sid];
    var infoBtn = '<button type="button" class="info-btn" data-sinfo="'+sid+'" aria-expanded="'+infoOpen+'" aria-label="'+(infoOpen?'بستن اطلاعات فروشگاه':'اطلاعات کامل فروشگاه')+'" title="'+(infoOpen?'بستن اطلاعات':'اطلاعات کامل فروشگاه')+'">'+IC.info+'</button>';
    return '<li style="--i:'+Math.min(i||0,10)+'"><article class="card dcard'+(sel?' sel':'')+'" data-sid="'+sid+'">' +
      '<button type="button" class="card-main" data-sid="'+sid+'" aria-pressed="'+sel+'">' +
        '<span class="c-body">' +
          '<span class="c-row"><span class="c-nm">'+badgeHTML(st)+'<span class="c-name" data-full="'+esc(st.name)+'">'+st.name+'</span></span>'+payIcons(st)+(st.fast ? '<span class="tag fast" data-hint="'+esc(st.fast)+'">'+IC.truck+'ارسال فوری</span>' : '')+'</span>' +
          '<span class="c-var"><span>'+KIND_NAME[storeKind(sid)]+'</span>'+rateHTML(st)+'</span>' +
          '<span class="c-meta">'+statusHTML(st)+'<span>'+fa1(km)+' کیلومتر</span>'+etaHTML(km, sid)+'</span>' +
          '<span class="c-addr">'+esc(st.addr)+'</span>' +
        '</span>' +
        '<span class="d-art" aria-hidden="true">'+storeArtHTML(sid)+'</span>' +
      '</button>' + infoBtn +
      (infoOpen ? storeDetHTML(sid, st, km, {}) : '') +
    '</article></li>';
  }

  /* ---------- پنجرهٔ اطلاعات فروشگاه (از تربچت، نقشهٔ بدون جستجو، ...) ---------- */
  var storeDlg = $('#storeDlg'), sdlg = null;
  function storeDlgHTML(){
    var sid = sdlg.sid, st = STORES[sid], km = roadKm(state.origin, st), o = null;
    if(sdlg.cat){ var r = (OFFERS[sdlg.cat]||[]).filter(function(x){ return x[0]===sid && (!sdlg.title || x[1]===sdlg.title); })[0]; if(r) o = mk(r, sdlg.cat); }
    return '<div class="sd-top"><span class="sd-art" aria-hidden="true">'+storeArtHTML(sid)+'</span><div class="sd-info">' +
        '<div class="c-nm">'+badgeHTML(st)+'<b class="sd-name">'+esc(st.name)+'</b>'+payIcons(st)+'</div>' +
        '<div class="c-var"><span>'+KIND_NAME[storeKind(sid)]+'</span>'+rateHTML(st)+'</div>' +
        '<div class="c-meta">'+statusHTML(st)+'<span>'+fa1(km)+' کیلومتر</span>'+etaHTML(km, sid)+'</div>' +
        '<button type="button" class="sd-guide" data-guide="'+sid+'">'+IC.route+'راهنمای رسیدن به فروشگاه</button></div></div>' +
      (o ? '<div class="sd-offer"><div class="sd-o-t"><b>'+esc(o.title)+'</b><span class="c-var">'+colorsHTML(o.colors)+'</span></div>' +
        '<div class="sd-o-p"><span class="sd-price"><b>'+fa(o.price)+'</b> تومان</span><span class="stock '+o.stock+'">'+STOCK[o.stock]+'</span>'+updHTML(o.hrs)+'</div></div>' : '') +
      storeDetHTML(sid, st, km, {extraRow: o ? extraRowHTML(sdlg.cat, o.extra) : '', buy: o && st.website ? st.website.replace(/\/$/,'')+'/search?q='+encodeURIComponent(o.title) : ''});
  }
  function openStoreDlg(sid, cat, title){
    if(!STORES[sid]) return;
    sdlg = {sid: sid, cat: cat || null, title: title || ''};
    $('#storeDlgTitle').textContent = 'اطلاعات فروشگاه';
    $('#storeDlgBody').innerHTML = storeDlgHTML();
    if(!storeDlg.open){ if(typeof storeDlg.showModal==='function') storeDlg.showModal(); else storeDlg.setAttribute('open',''); }
    $('#storeDlgBody').scrollTop = 0;
  }
  $('#storeDlgClose').addEventListener('click', function(){ storeDlg.close(); });
  storeDlg.addEventListener('click', function(e){
    if(e.target===storeDlg){ storeDlg.close(); return; }
    var g = e.target.closest('[data-guide]');
    if(g){ storeDlg.close(); goView('agent'); NQ.AgentUI.askGuide(g.getAttribute('data-guide')); return; }
    var t = e.target.closest('[data-showmap]');
    if(t){ storeDlg.close(); if(sdlg.cat) openStoreFrom(sdlg.cat, sdlg.sid, sdlg.title, 'map'); else storeOnMap(sdlg.sid); return; }
    var body = $('#storeDlgBody'), y = body.scrollTop;
    if(storeAction(e, body)){ if(storeDlg.open){ body.innerHTML = storeDlgHTML(); body.scrollTop = y; } }
  });
  document.addEventListener('click', function(e){
    var t = e.target.closest && e.target.closest('[data-act="nearme"],[data-act="allmap"],[data-act="cleardir"],[data-act="clearnear"]');
    if(!t) return;
    var a = t.getAttribute('data-act');
    if(a==='nearme') showArea(areaQuery({place: 'me', kind: 'all'}), view==='map' ? 'map' : 'list');
    else if(a==='allmap') goView('map');
    else if(a==='cleardir'){ state.dir = null; state.selected = null; renderAll(); fitResults(); }
    else { state.filters.near = null; afterFilterChange(); fitResults(); }
  });

  /* ---------- اطلاعات فروشگاه: تماس، نقشه، روش رفت‌وآمد ---------- */
  function revealStore(sid){
    quietMap(); requestAnimationFrame(function(){ MapView.reveal(sid, STORES[sid], 20); });
  }
  var callDlg = $('#callDlg');
  function openCallDlg(){ if(callDlg.open) return; if(typeof callDlg.showModal==='function') callDlg.showModal(); else callDlg.setAttribute('open',''); }
  function phonesHTML(st){
    return st.phones.map(function(p){
      return '<a class="call-opt" href="tel:'+toTel(p)+'"><span class="co-ic">'+IC.phone+'</span>' +
        '<span class="co-t"><b dir="ltr">'+p+'</b><small>'+(isMobileNo(p)?'همراه':'ثابت')+'</small></span><span class="co-go">تماس</span></a>';
    }).join('');
  }
  /* تماس مستقیم: یک شماره = همان لحظه تماس؛ چند شماره = انتخاب شماره */
  function callStore(sid, back){
    var st = STORES[sid]; if(!st) return;
    if(st.phones.length<2){ if(callDlg.open) callDlg.close(); window.location.href = 'tel:'+toTel(st.phones[0]); return; }
    $('#callTitle').textContent = 'با کدام شماره تماس می‌گیرید؟';
    $('#callStore').textContent = st.name;
    $('#callList').innerHTML = phonesHTML(st) +
      (back ? '<button type="button" class="link-btn call-back" data-inq="'+sid+'">بازگشت به گزینه‌های استعلام</button>' : '');
    openCallDlg();
  }
  /* استعلام قیمت: «خودم تماس می‌گیرم» یا «ترب برایم استعلام بگیرد» (سرویس استعلام بعداً وصل می‌شود) */
  function openInquiry(sid){
    var st = STORES[sid]; if(!st) return;
    if(!inqOn(st)){ callStore(sid); return; }
    var c = inqContext(sid), same = inqs.filter(function(q){ return q.sid===sid && q.title===c.title; });
    var sent = same.some(function(q){ return q.status==='pending'; }), valid = same.filter(inqValid)[0];
    var what = c.title || (catById(c.cat)||{}).name || '';
    $('#callTitle').textContent = 'استعلام قیمت و موجودی';
    $('#callStore').textContent = st.name + (what ? ' · ' + what : '');
    $('#callList').innerHTML =
      '<button type="button" class="inq-opt" data-inq-self="'+sid+'">' +
        '<span class="co-ic">'+IC.phone+'</span>' +
        '<span class="co-t"><b>خودم تماس می‌گیرم <em class="inq-badge fast">فوری</em></b><small>تماس با فروشگاه برای استعلام قیمت و موجودی'+(st.phones.length>1?' ('+fa(st.phones.length)+' شماره)':'')+'</small></span></button>' +
      '<button type="button" class="inq-opt torob" data-inq-torob="'+sid+'"'+(sent||valid?' disabled aria-disabled="true"':'')+'>' +
        '<span class="co-ic">'+IC.agent+'</span>' +
        '<span class="co-t"><b>'+(sent ? 'درخواست استعلام ثبت شد' : valid ? 'پاسخ معتبر داریم: '+fa(valid.answer.price)+' تومان · '+(valid.answer.stock==='in' ? 'موجود' : 'ناموجود') : 'ترب برایم استعلام بگیرد <em class="inq-badge slow">تا ۲۰ دقیقه ممکن است طول بکشد</em>')+'</b><small>'+(sent
          ? 'به‌محض پاسخ فروشنده خبرتان می‌کنیم؛ در صفحهٔ «استعلام‌ها» هم می‌بینید.'
          : valid ? 'این پاسخ تا '+leftTxt(valid.answer.at + INQ_VALID - Date.now())+' دیگر معتبر است؛ در صفحهٔ «استعلام‌ها» می‌بینید. اگر شک دارید، خودتان تماس بگیرید.'
          : 'ما با فروشنده ارتباط برقرار می‌کنیم و برایتان استعلام موجودی و قیمت را می‌گیریم.')+'</small></span></button>';
    openCallDlg();
  }
  $('#callClose').addEventListener('click',function(){callDlg.close()});
  callDlg.addEventListener('click',function(e){
    var t;
    if(e.target===callDlg || e.target.closest('.call-opt')){ callDlg.close(); return; }
    if((t = e.target.closest('[data-inq-self]'))){ callStore(t.getAttribute('data-inq-self'), true); return; }
    if((t = e.target.closest('[data-inq]'))){ openInquiry(t.getAttribute('data-inq')); return; }
    if((t = e.target.closest('[data-inq-torob]'))){
      var sid = t.getAttribute('data-inq-torob'), c = inqContext(sid);
      createInq(sid, c.cat, c.title); callDlg.close();
      toast('درخواست استعلام از «'+STORES[sid].name+'» ثبت شد؛ جوابش در صفحهٔ «استعلام‌ها» می‌آید.', 'success');
    }
  });
  function showOnMap(sid){
    if(!STORES[sid]) return;
    if(state.tab==='plan') state.planSel = sid;
    else if(!state.compare) state.selected = sid;
    if(view!=='map') goView('map', {noFit:true});   // از صفحهٔ فهرست به صفحهٔ نقشه
    setSheet('peek');   // موبایل: فهرست پایین می‌رود تا نقشه دیده شود
    renderAll(); revealStore(sid);
    var m = $('#map'); if(!isMobile() && m && m.scrollIntoView) m.scrollIntoView({block:'nearest',behavior:reduced?'auto':'smooth'});
  }
  /* کلیک روی دکمه‌های «اطلاعات بیشتر» (کارت نتایج و کارت برنامهٔ سر زدن)؛ اگر مربوط به آنها بود true */
  function storeAction(e, root){
    var t = e.target.closest('[data-smode]'), sid;
    if(t){
      sid = t.getAttribute('data-sid'); var id = t.getAttribute('data-smode');
      Travel.setFor(sid, Travel.modeFor(sid)===id ? null : id);
      afterFilterChange();
      var again = root.querySelector('[data-smode="'+id+'"][data-sid="'+sid+'"]'); if(again) again.focus({preventScroll:true});
      return true;
    }
    if((t = e.target.closest('[data-smode-reset]'))){ Travel.setFor(t.getAttribute('data-smode-reset'), null); afterFilterChange(); return true; }
    if((t = e.target.closest('[data-paymore]')) || (t = e.target.closest('[data-score]'))){
      var pm = t.hasAttribute('data-paymore'), key = pm ? 'data-paymore' : 'data-score', bag = pm ? state.payOpen : state.scoreOpen;
      sid = t.getAttribute(key);
      if(bag[sid]) delete bag[sid]; else bag[sid] = true;
      renderAll();
      var again = root.querySelector('['+key+'="'+sid+'"]'); if(again) again.focus({preventScroll:true});
      return true;
    }
    if((t = e.target.closest('[data-report]'))){ openReport(t.getAttribute('data-report')); return true; }
    if((t = e.target.closest('[data-inq]'))){ openInquiry(t.getAttribute('data-inq')); return true; }
    if((t = e.target.closest('[data-call]'))){ callStore(t.getAttribute('data-call')); return true; }
    if((t = e.target.closest('[data-showmap]'))){ showOnMap(t.getAttribute('data-showmap')); return true; }
    return false;
  }

  /* ---------- actions ---------- */
  var enterTimer = 0;
  function setCat(id){
    var changed = id!==state.cat || !!state.dir;
    state.dir = null;
    state.cat = id; state.tab = 'results'; state.planSel = null;
    if(changed){state.picks={A:null,B:null};state.selected=null;state.product=null;state.info=false;state.pinfo={};state.sinfo={};state.gx=null;state.pmore={};state.pcmp=[];state.filters=defFilters();var ps=prodsOf(id);if(ps.length===1) state.product=ps[0].id}
    if(changed){cardsEl.classList.add('enter');clearTimeout(enterTimer);enterTimer=setTimeout(function(){cardsEl.classList.remove('enter')},900)}
    if(changed) bump(prodsEl);
    if(changed) setSheet(autoSheet());
    renderAll();
    if(changed) fitResults();
  }
  function togglePick(sid){
    var p = state.picks;
    if(p.A===sid) p.A=null;
    else if(p.B===sid) p.B=null;
    else if(!p.A) p.A=sid;
    else if(!p.B) p.B=sid;
    else p.B=sid;
    renderAll();
    if(p.A && p.B){
      fitPoints([state.origin,STORES[p.A],STORES[p.B]]);
      listTop(true);
    } else if(p.A===sid || p.B===sid) revealStore(sid);
  }
  /* برنامهٔ سر زدن: انتخاب فروشگاه = انتخاب روی نقشه + باز شدن اطلاعات تکمیلی؛ دوباره زدن = لغو */
  function planFocus(sid, force){
    var on = force===undefined ? state.planSel!==sid : force;
    if(on){ if(state.planSel && state.planSel!==sid) delete state.planInfo[state.planSel]; state.planSel = sid; state.planInfo[sid] = true; }
    else { if(state.planSel===sid) state.planSel = null; delete state.planInfo[sid]; }
    if(on) setSheet('full');
    renderAll();
    if(on){
      revealStore(sid);
      requestAnimationFrame(function(){
        var el = planList.querySelector('.pcard[data-sid="'+sid+'"]');
        if(el) el.scrollIntoView({block:'nearest',behavior:reduced?'auto':'smooth'});
      });
    }
  }
  function activate(sid,from){
    if(state.tab==='plan'){ if(state.planCmp) planPick(sid); else planFocus(sid); return; }
    if(stage()==='pick'){ pickFromPin(sid); return; }
    if(stage()==='none'){ openStoreDlg(sid); return; }   // بدون جستجو: پنجرهٔ اطلاعات فروشگاه
    if(state.compare && stage()!=='dir') togglePick(sid);
    else {
      state.selected = state.selected===sid ? null : sid;
      if(!state.selected) delete state.sinfo[sid];
      /* موبایل: از فهرست ← تمام‌صفحه تا اطلاعات دیده شود؛ از نقشه ← نیمه‌باز تا نقشه هم بماند */
      if(state.selected) setSheet(from==='pin' ? 'half' : 'full', from==='pin');
      renderAll();
      if(state.selected) revealStore(sid);
      if(from==='pin' && state.selected){
        requestAnimationFrame(function(){
          var el = cardsEl.querySelector('.card[data-sid="'+sid+'"]');
          if(el) el.scrollIntoView({block:isMobile() ? 'start' : 'nearest',behavior:reduced||isMobile()?'auto':'smooth'});
        });
      }
    }
  }

  /* ---------- events: list, search, toolbar ---------- */
  cardsEl.addEventListener('click',function(e){
    if(storeAction(e, cardsEl)) return;
    var sv = e.target.closest('.save-btn'); if(sv){toggleSave(sv.getAttribute('data-save'));return}
    var ib = e.target.closest('[data-sinfo]'); if(ib){toggleStoreInfo(ib.getAttribute('data-sinfo'));return}
    var b = e.target.closest('.card-main'); if(!b) return;
    var sid = b.getAttribute('data-sid');
    /* اگر اطلاعات فروشگاه (بدون انتخاب) باز است، کلیک اول فقط آن را می‌بندد؛ کلیک بعدی انتخاب می‌کند */
    if(state.sinfo[sid] && !(state.selected===sid && !state.compare)){ toggleStoreInfo(sid); return; }
    activate(sid,'list');
  });
  cmpEl.addEventListener('click',function(e){
    var x = e.target.closest('[data-unpick]');
    if(x){state.picks[x.getAttribute('data-unpick')]=null;renderAll();return}
    if(e.target.closest('#cmpClose')){state.compare=false;state.picks={A:null,B:null};renderAll()}
  });
  function togglePMore(id, root){
    if(state.pmore[id]) delete state.pmore[id]; else state.pmore[id] = true;
    renderAll(); var b = root.querySelector('[data-pmore="'+id+'"]'); if(b) b.focus({preventScroll:true});
  }
  prodsEl.addEventListener('click',function(e){
    var t;
    if((t = e.target.closest('[data-pmore]'))){ togglePMore(t.getAttribute('data-pmore'), prodsEl); return; }
    if((t = e.target.closest('[data-pinfo]'))){
      var id = t.getAttribute('data-pinfo'); togglePInfo(id);
      var again = prodsEl.querySelector('[data-pinfo="'+id+'"]'); if(again) again.focus({preventScroll:true});
      if(state.pinfo[id]){ var d = $('#pd-'+id); if(d) requestAnimationFrame(function(){ d.scrollIntoView({block:'nearest',behavior:reduced?'auto':'smooth'}); }); }
      return;
    }
    if((t = e.target.closest('[data-pcmp]'))){
      var pid = t.getAttribute('data-pcmp'); togglePCmp(pid);
      var b2 = prodsEl.querySelector('[data-pcmp="'+pid+'"]'); if(b2) b2.focus({preventScroll:true});
      return;
    }
    if((t = e.target.closest('[data-prod]'))){
      var pid2 = t.getAttribute('data-prod');
      /* وقتی «مشاهدهٔ جزئیات» باز است، کلیک اول روی محصول فقط جزئیات را می‌بندد؛ کلیک بعدی انتخاب می‌کند */
      if(t.classList.contains('prod-main') && state.pinfo[pid2]){ togglePInfo(pid2); return; }
      selectProduct(pid2);
    }
  });
  pcmpEl.addEventListener('click',function(e){
    var t;
    if((t = e.target.closest('[data-punpick]'))){ var ui = state.pcmp.indexOf(t.getAttribute('data-punpick')); if(ui>-1) state.pcmp.splice(ui, 1); renderAll(); return; }
    if(e.target.closest('#pcmpClose')){ state.pcmp = []; renderAll(); return; }
    if(e.target.closest('[data-pcmp-full]')){ openFullCmp(); return; }
    if((t = e.target.closest('[data-prod]'))) selectProduct(t.getAttribute('data-prod'));
  });
  pickBarEl.addEventListener('click',function(e){
    var pm = e.target.closest('[data-pmore]'); if(pm){ togglePMore(pm.getAttribute('data-pmore'), pickBarEl); return; }
    if(e.target.closest('#spMore')){toggleInfo();return}
    if(e.target.closest('#spCmp')){compareFromBar();return}
    if(e.target.closest('#spChange')) clearProduct();
  });
  $('#chips').addEventListener('click',function(e){
    var b = e.target.closest('.chip'); if(!b) return;
    var c = catById(b.getAttribute('data-cat'));
    if(view==='agent') goView('list');
    qEl.value = c.name; setCat(c.id);
    if(isMobile()) setTopMin(true);
  });
  qEl.addEventListener('input',function(){ if(view==='agent') goView('list'); var c=findCat(qEl.value);setCat(c?c.id:null)});
  qEl.addEventListener('focus',function(){ if(topMin) setTopMin(false); });
  $('#searchForm').addEventListener('submit',function(e){e.preventDefault();qEl.blur(); if(isMobile()) setTopMin(true);});
  $('#clearQ').addEventListener('click',function(){qEl.value='';setCat(null);qEl.focus()});
  $('#sort').addEventListener('click',function(e){
    var b = e.target.closest('button'); if(!b) return;
    state.sort = b.getAttribute('data-sort'); renderAll();
  });
  $('#cmpToggle').addEventListener('click',function(){
    if(state.tab==='plan'){
      state.planCmp = !state.planCmp; state.pPicks = {A:null,B:null}; state.pCat = null;
      if(state.planCmp){ state.planSel = null; state.planInfo = {}; }
      renderAll(); if(state.planCmp) listTop(true); else fitPlan();
      return;
    }
    state.compare = !state.compare;
    state.selected = null;
    if(!state.compare) state.picks={A:null,B:null};
    renderAll();
    if(state.compare) listTop(true);
  });

  /* ---------- events: برنامهٔ سر زدن ---------- */
  $('#planCmp').addEventListener('click',function(e){
    var t;
    if((t = e.target.closest('[data-unpick]'))){ state.pPicks[t.getAttribute('data-unpick')] = null; syncPlanPicks(); renderAll(); return; }
    if((t = e.target.closest('[data-pcat]'))){ state.pCat = t.getAttribute('data-pcat'); renderAll(); return; }
    if(e.target.closest('[data-pcmp-close]')){ state.planCmp = false; state.pPicks = {A:null,B:null}; state.pCat = null; renderAll(); fitPlan(); }
  });
  $('#tabResults').addEventListener('click',function(){setTab('results')});
  $('#tabPlan').addEventListener('click',function(){setTab('plan')});
  $('#planSort').addEventListener('click',function(e){
    var b = e.target.closest('button'); if(!b) return;
    Plan.setMode(b.getAttribute('data-pmode'), state.origin); renderAll(); fitPlan();
  });
  $('#departTime').addEventListener('change',function(e){Plan.setDepart(e.target.value); renderAll()});
  $('#departNow').addEventListener('click',function(){Plan.setDepart(null); renderAll()});
  $('#planClear').addEventListener('click',function(){
    if(!window.confirm('همهٔ فروشگاه‌های ذخیره‌شده پاک شوند؟')) return;
    Plan.clear(); state.planSel = null; renderAll(); fitResults();
  });
  planList.addEventListener('click',function(e){
    var pd = e.target.closest('[data-ppd]');
    if(pd){ var k = pd.getAttribute('data-ppd'); if(state.ppd[k]) delete state.ppd[k]; else state.ppd[k] = true; renderAll();
      var again = planList.querySelector('[data-ppd="'+k+'"]'); if(again) again.focus({preventScroll:true}); return; }
    var pm = e.target.closest('[data-pmore]'); if(pm){ togglePMore(pm.getAttribute('data-pmore'), planList); return; }
    if(storeAction(e, planList)) return;
    var b = e.target.closest('[data-act]');
    if(!b){
      /* کلیک روی خود کارت (نه دکمه‌ها، لینک‌ها، چک‌باکس یا بخش اطلاعات) = انتخاب روی نقشه + اطلاعات */
      if(e.target.closest('a,button,input,label,select,textarea,.det,[data-tip],[data-copy],[data-gal],.gview,.ppd')) return;
      if(window.getSelection && String(window.getSelection()).length) return;   // در حال انتخاب متن
      var card = e.target.closest('.pcard'); if(card){ if(state.planCmp) planPick(card.getAttribute('data-sid')); else planFocus(card.getAttribute('data-sid')); }
      return;
    }
    if(b.tagName==='INPUT') return;
    var act = b.getAttribute('data-act'), sid = b.getAttribute('data-sid');
    if(act==='done'){
      var stp = planStop(sid); Plan.setDone(sid, !(stp && stp.done)); renderAll();
      var vb = planList.querySelector('[data-act="done"][data-sid="'+sid+'"]'); if(vb) vb.focus({preventScroll:true});
    } else if(act==='up' || act==='down'){
      Plan.move(sid, act==='up' ? -1 : 1); renderAll();
      var again = planList.querySelector('[data-act="'+act+'"][data-sid="'+sid+'"]:not(:disabled)') || planList.querySelector('[data-act="focus"][data-sid="'+sid+'"]');
      if(again) again.focus();
    } else if(act==='rm'){
      Plan.remove(sid); if(state.planSel===sid) state.planSel=null; renderAll();
    } else if(act==='rmcat'){
      Plan.removeCat(sid, b.getAttribute('data-cat')); renderAll();
    } else if(act==='focus'){
      if(state.planCmp) planPick(sid); else planFocus(sid);
    }
  });

  /* ---------- events: map ---------- */
  var ZOOM_NOTE = 'موقعیت شما از فروشگاه‌های نمونه (تهران) خیلی دور است. برای نمایش، همان نقطهٔ پیش‌فرض نگه داشته شد.';
  var GEO_ERR = {
    denied: 'اجازهٔ دسترسی به موقعیت داده نشد. می‌توانید نقطهٔ «شما» را روی نقشه بکشید.',
    unsupported: 'مرورگر شما موقعیت‌یابی را پشتیبانی نمی‌کند.',
    failed: 'موقعیت شما پیدا نشد. دوباره امتحان کنید یا نقطهٔ «شما» را بکشید.'
  };
  $('#zin').addEventListener('click', function () { MapView.zoomIn(); });
  $('#zout').addEventListener('click', function () { MapView.zoomOut(); });
  $('#zfit').addEventListener('click', function () {
    if (state.tab === 'results' && state.compare && state.picks.A && state.picks.B) fitPoints([state.origin, STORES[state.picks.A], STORES[state.picks.B]]);
    else fitCurrent();
  });
  $('#zclu').addEventListener('click', function () {
    var on = !MapView.getCluster(); MapView.setCluster(on); this.setAttribute('aria-pressed', String(on));
    toast(on ? 'فروشگاه‌های نزدیک هم در زوم‌اوت گروه‌بندی می‌شوند.' : 'گروه‌بندی خاموش شد؛ همهٔ فروشگاه‌ها جدا نمایش داده می‌شوند.', 'info');
  });
  /* موقعیت واقعی (GPS). silent: بدون پیام خطا (برای موقعیت‌یابی خودکار هنگام باز شدن) */
  function locateMe(silent) {
    var btn = $('#zloc'); btn.disabled = true;
    MapView.locate(function (ll) {
      btn.disabled = false;
      var nearest = Math.min.apply(null, Object.keys(STORES).map(function (k) { return NQ.geo.distanceKm(ll, STORES[k]); }));
      if (nearest > 60) { if (!silent) toast(ZOOM_NOTE, 'warn'); return; }
      state.origin = ll; you_hint.hidden = true;   // موقعیت واقعی داریم؛ راهنمای «بکشید» لازم نیست
      renderAll(); fitCurrent();
    }, function (code) { btn.disabled = false; if (!silent) toast(GEO_ERR[code] || GEO_ERR.failed, 'warn'); });
  }
  $('#zloc').addEventListener('click', function () { locateMe(false); });
  /* اگر اجازهٔ موقعیت از قبل داده شده، بی‌صدا موقعیت گرفته می‌شود (بدون پرسیدن دوباره از کاربر) */
  try {
    if (navigator.permissions && navigator.geolocation) navigator.permissions.query({ name: 'geolocation' }).then(function (p) { if (p.state === 'granted') locateMe(true); }, function () {});
  } catch (e) {}


  /* ---------- انتخاب شهر (منوی سفارشی، نه select معمولی) ---------- */
  var cityBtn = $('#cityBtn'), cityPop = $('#cityPop'), cityQ = $('#cityQ'), cityList = $('#cityList');
  var curCity = 'tehran', cityHi = 0, cityItems = [];
  function cityMatches(){
    var q = norm(cityQ.value);
    return NQ.CITIES.filter(function(c){return !q || norm(c.name).indexOf(q)>-1});
  }
  function renderCities(){
    cityItems = cityMatches();
    if(cityHi>=cityItems.length) cityHi = Math.max(0,cityItems.length-1);
    cityList.innerHTML = cityItems.length ? cityItems.map(function(c,i){
      return '<li role="option" id="city-'+c.id+'" class="city-opt'+(i===cityHi?' hi':'')+(c.active?'':' off')+(c.id===curCity?' cur':'')+'" data-city="'+c.id+'" aria-selected="'+(c.id===curCity)+'" aria-disabled="'+!c.active+'">' +
        '<span>'+esc(c.name)+'</span>'+(c.id===curCity?'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>':(c.active?'':'<small>به‌زودی</small>'))+'</li>';
    }).join('') : '<li class="city-empty">شهری با این نام پیدا نشد. فعلاً فقط تهران فعال است.</li>';
    var hi = cityItems[cityHi]; if(hi) cityQ.setAttribute('aria-activedescendant','city-'+hi.id); else cityQ.removeAttribute('aria-activedescendant');
  }
  function openCity(){
    cityQ.value = ''; cityHi = 0; renderCities();
    cityPop.hidden = false; cityBtn.setAttribute('aria-expanded','true');
    cityQ.focus();
  }
  function closeCity(focusBtn){
    if(cityPop.hidden) return;
    cityPop.hidden = true; cityBtn.setAttribute('aria-expanded','false');
    if(focusBtn) cityBtn.focus();
  }
  function pickCity(id){
    var c = NQ.CITIES.filter(function(x){return x.id===id})[0];
    if(!c) return;
    if(!c.active){ toast('«'+c.name+'» به‌زودی اضافه می‌شود. فعلاً فقط تهران فعال است.','info'); return; }
    setCity(c.id);
    closeCity(true); fitCurrent();
  }
  /* شهر انتخاب‌شده (از منوی شهر یا «شهر پیش‌فرض» در تنظیمات) ذخیره می‌شود */
  function setCity(id){
    var c = NQ.CITIES.filter(function(x){return x.id===id && x.active})[0]; if(!c) return false;
    curCity = c.id; $('#cityName').textContent = c.name;
    try { localStorage.setItem('nq-city', c.id); } catch (e) {}
    return true;
  }
  try { var savedCity = localStorage.getItem('nq-city'); if(savedCity) setCity(savedCity); } catch (e) {}
  cityBtn.addEventListener('click',function(){ cityPop.hidden ? openCity() : closeCity(true) });
  cityQ.addEventListener('input',function(){cityHi=0; renderCities()});
  cityQ.addEventListener('keydown',function(e){
    if(e.key==='ArrowDown'){e.preventDefault(); if(cityItems.length){cityHi=(cityHi+1)%cityItems.length; renderCities()}}
    else if(e.key==='ArrowUp'){e.preventDefault(); if(cityItems.length){cityHi=(cityHi-1+cityItems.length)%cityItems.length; renderCities()}}
    else if(e.key==='Enter'){e.preventDefault(); if(cityItems[cityHi]) pickCity(cityItems[cityHi].id)}
    else if(e.key==='Escape'){e.stopPropagation(); closeCity(true)}
  });
  cityList.addEventListener('click',function(e){
    var li = e.target.closest('[data-city]'); if(li) pickCity(li.getAttribute('data-city'));
  });
  cityList.addEventListener('mousemove',function(e){
    var li = e.target.closest('[data-city]'); if(!li) return;
    var i = cityItems.map(function(c){return c.id}).indexOf(li.getAttribute('data-city'));
    if(i>-1 && i!==cityHi){cityHi=i; Array.prototype.forEach.call(cityList.children,function(n,k){n.classList.toggle('hi',k===i)})}
  });
  document.addEventListener('click',function(e){ if(!cityPop.hidden && !e.target.closest('#city')) closeCity(false) });

  /* حالت روشن/تاریک و منوی حساب: js/account.js */

  /* ---------- راهنمای آیکون‌ها (tooltip): با hover، فوکوس یا کلیک بالای آیکون نمایش داده می‌شود ---------- */
  var tipEl = document.createElement('div'), tipFor = null, tipPinned = false;
  tipEl.className = 'tip'; tipEl.setAttribute('role','tooltip'); tipEl.id = 'nqTip'; tipEl.hidden = true;
  document.body.appendChild(tipEl);
  function placeTip(el){
    var r = el.getBoundingClientRect(), w = tipEl.offsetWidth, h = tipEl.offsetHeight, vw = document.documentElement.clientWidth;
    var cx = r.left + r.width/2, left = clamp(cx - w/2, 8, vw - w - 8), top = r.top - h - 9, below = top < 8;
    if(below) top = r.bottom + 9;
    tipEl.classList.toggle('below', below);
    tipEl.style.left = left + 'px'; tipEl.style.top = top + 'px';
    tipEl.style.setProperty('--ax', clamp(cx - left, 12, w - 12) + 'px');
  }
  function showTip(el, pin){
    if(tipFor && tipFor!==el) tipFor.removeAttribute('aria-describedby');
    tipFor = el; tipPinned = !!pin;
    tipEl.textContent = el.getAttribute('data-tip') || el.getAttribute('data-hint') || el.getAttribute('data-full');
    tipEl.hidden = false; placeTip(el);
    el.setAttribute('aria-describedby', 'nqTip');
  }
  function hideTip(){ if(!tipFor) return; tipFor.removeAttribute('aria-describedby'); tipFor = null; tipPinned = false; tipEl.hidden = true; }
  /* نام‌های طولانی با «...» کوتاه می‌شوند؛ با hover (فقط وقتی واقعاً بریده شده) نام کامل نشان داده می‌شود و کلیک مثل قبل کار می‌کند */
  function cut(el){ return el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 2; }
  function fullTarget(e){ var f = e.target.closest && e.target.closest('[data-full]'); return f && cut(f) ? f : null; }
  document.addEventListener('mouseover', function(e){
    var t = (e.target.closest && (e.target.closest('[data-tip]') || e.target.closest('[data-hint]'))) || fullTarget(e);
    if(t){ if(t!==tipFor) showTip(t, false); }
    else if(tipFor && !tipPinned) hideTip();
  });
  document.addEventListener('focusin', function(e){ var t = e.target.closest && (e.target.closest('[data-tip]') || e.target.closest('[data-hint]')); if(t) showTip(t, false); else if(tipFor && !tipPinned) hideTip(); });
  /* کلیک روی آیکونِ راهنما فقط راهنما را نشان می‌دهد و کارت/دکمهٔ پشتش را فعال نمی‌کند */
  document.addEventListener('click', function(e){
    var t = e.target.closest && e.target.closest('[data-tip]');
    if(t){
      e.stopPropagation(); e.preventDefault();
      var href = t.getAttribute('data-href');
      if(href){ hideTip(); window.open(href, '_blank', 'noopener'); return; }   // ضمانت ترب / ترب‌پی: صفحهٔ توضیحات باز می‌شود
      if(tipFor===t && tipPinned) hideTip(); else showTip(t, true);
      return;
    }
    if(tipFor) hideTip();
  }, true);
  document.addEventListener('keydown', function(e){
    if(e.key==='Escape') hideTip();
    if((e.key==='Enter'||e.key===' ') && e.target.getAttribute && e.target.getAttribute('data-href')){ e.preventDefault(); window.open(e.target.getAttribute('data-href'), '_blank', 'noopener'); }
  });
  window.addEventListener('scroll', hideTip, true);
  window.addEventListener('resize', hideTip);

  /* راهنمای ترب (دکمهٔ ؟ سمت راست مقایسه) */
  var helpDlg = $('#helpDlg');
  var plainGuar = guaranteeHTML({guarantee:true}).replace(/ data-(tip|href)="[^"]*"/g,'').replace('role="link" tabindex="-1"','role="img"');
  $('#helpBody').innerHTML =
    '<ul class="help-list">' +
      '<li><span class="h-ic">'+plainGuar+'</span><span><b>ضمانت ترب</b>اگر خرید از فروشگاهی که این نشان را دارد به مشکل بخورد (کالا با توضیحات یکی نباشد یا تحویل داده نشود)، ترب پیگیری می‌کند.'+extLink(LINKS.guarantee,'توضیحات کامل ضمانت ترب')+'</span></li>' +
      '<li><span class="h-ic">'+IC.torobpay+'</span><span><b>ترب‌پی</b>خرید قسطی؛ پرداخت در ۴ قسط بدون کارمزد. فروشگاه‌هایی که ترب‌پی دارند ضمانت ترب هم دارند، برای همین کنار نامشان فقط آیکون ترب‌پی می‌آید.'+extLink(LINKS.torobpay,'سایت ترب‌پی')+'</span></li>' +
      '<li><span class="h-ic"><span class="pay ins">'+IC.installment+'</span></span><span><b>خرید اقساطی</b>فروشگاه روش‌های دیگری برای خرید قسطی هم دارد. در اطلاعات فروشگاه روی «پرداخت قسطی» بزنید تا همه را ببینید.</span></li>' +
      '<li><span class="h-ic"><span class="rate">'+IC.star+'<b>۴٫۶</b></span></span><span><b>امتیاز فروشگاه</b>امتیاز ۱ تا ۵ و مدت حضور فروشگاه در ترب. در اطلاعات فروشگاه روی امتیاز بزنید تا جزئیات ارزیابی را ببینید.'+extLink(LINKS.score,'شیوه ارزیابی فروشگاه')+'</span></li>' +
    '</ul>' +
    '<a class="help-link" href="'+LINKS.safe+'" target="_blank" rel="noopener">'+IC.info+'<span>راهنمای خرید امن ترب</span></a>';
  $('#helpBtn').innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.6 9.3a2.5 2.5 0 0 1 4.8 1c0 1.7-2.4 2-2.4 3.5"/><path d="M12 17v.1"/></svg>'; $('#helpLogo').innerHTML = IC.torob;
  $('#helpBtn').addEventListener('click', function(){ if(typeof helpDlg.showModal==='function') helpDlg.showModal(); else helpDlg.setAttribute('open',''); });
  $('#helpClose').addEventListener('click', function(){ helpDlg.close(); });
  helpDlg.addEventListener('click', function(e){ if(e.target===helpDlg) helpDlg.close(); });

  /* آیکون‌های تب‌ها و راهنمای «پیشنهادی» */
  $('#tabResIc').innerHTML = IC.list; $('#tabPlanIc').innerHTML = IC.bookmark;
  var smartBtn = document.querySelector('#sort [data-sort="smart"]');
  smartBtn.insertAdjacentHTML('beforeend', '<span class="qtip" role="img" aria-label="'+esc(TIPS.smart)+'" data-tip="'+esc(TIPS.smart)+'">'+IC.info+'</span>');

  /* ---------- گالری تصاویر ---------- */
  var swipeAt = 0, uiTimer = 0;
  function gStep(d){
    var g = state.gx; if(!g) return;
    var n = prodImages(prodOf(g.cat, g.pid), g.cat).length; g.i = (g.i + d + n) % n; renderAll();
  }
  function showUI(el){
    if(!el) return;
    el.classList.add('ui'); clearTimeout(uiTimer);
    uiTimer = setTimeout(function(){ if(!el.matches(':hover') && !el.contains(document.activeElement)) el.classList.remove('ui'); else showUI(el); }, 2600);
  }
  function syncGview(){ var g = document.querySelector('.gview'); if(g) showUI(g); }
  document.addEventListener('pointermove', function(e){ var g = e.target.closest && e.target.closest('.gview'); if(g && !g.classList.contains('ui')) showUI(g); });
  /* تمام‌صفحه */
  var galDlg = $('#galDlg'), gal = null;
  function renderGal(){
    var p = prodOf(gal.cat, gal.pid), imgs = prodImages(p, gal.cat), n = imgs.length, im = imgs[gal.i];
    $('#galTitle').textContent = p.title;
    $('#galCount').textContent = fa(gal.i+1)+' / '+fa(n)+(im.cap?' · '+im.cap:'');
    $('#galStage').innerHTML = im.html;
    $('#galPrev').hidden = $('#galNext').hidden = n<2;
    $('#galThumbs').innerHTML = n>1 ? imgs.map(function(x,k){ return '<button type="button" class="gal-th'+(k===gal.i?' on':'')+'" data-gi="'+k+'" aria-label="تصویر '+fa(k+1)+'"'+(k===gal.i?' aria-current="true"':'')+'>'+x.html+'</button>'; }).join('') : '';
  }
  function galStep(d){ var n = prodImages(prodOf(gal.cat, gal.pid), gal.cat).length; gal.i = (gal.i + d + n) % n; renderGal(); }
  function openGallery(){
    var g = state.gx; if(!g) return;
    gal = {cat:g.cat, pid:g.pid, i:g.i}; renderGal();
    if(typeof galDlg.showModal==='function') galDlg.showModal(); else galDlg.setAttribute('open','');
  }
  function closeGallery(){ if(galDlg.open) galDlg.close(); }
  galDlg.addEventListener('close', function(){ if(gal && state.gx){ state.gx.i = gal.i; renderAll(); } gal = null; });
  $('#galClose').innerHTML = IC.x; $('#galPrev').innerHTML = IC.chevR; $('#galNext').innerHTML = IC.chevL;
  $('#galClose').addEventListener('click', closeGallery);
  $('#galPrev').addEventListener('click', function(){ galStep(-1); });
  $('#galNext').addEventListener('click', function(){ galStep(1); });
  $('#galThumbs').addEventListener('click', function(e){ var b = e.target.closest('[data-gi]'); if(b){ gal.i = +b.getAttribute('data-gi'); renderGal(); } });
  galDlg.addEventListener('keydown', function(e){
    if(e.key==='ArrowLeft'){ e.preventDefault(); galStep(1); }      // راست‌به‌چپ: بعدی سمت چپ است
    else if(e.key==='ArrowRight'){ e.preventDefault(); galStep(-1); }
  });
  /* لمس: چپ/راست = قبلی/بعدی، پایین = کوچک کردن (یا بستن تمام‌صفحه) */
  var tsw = null;
  document.addEventListener('touchstart', function(e){
    var g = e.target.closest && e.target.closest('.gview, #galStage'); if(!g || e.touches.length>1) { tsw = null; return; }
    var t = e.touches[0]; tsw = {x:t.clientX, y:t.clientY, g:g}; if(g.classList.contains('gview')) showUI(g);
  }, {passive:true});
  document.addEventListener('touchend', function(e){
    if(!tsw) return;
    var t = e.changedTouches[0], dx = t.clientX - tsw.x, dy = t.clientY - tsw.y, full = tsw.g.id==='galStage'; tsw = null;
    if(Math.abs(dx)>45 && Math.abs(dx)>Math.abs(dy)*1.2){ swipeAt = Date.now(); if(full) galStep(dx>0?1:-1); else gStep(dx>0?1:-1); }
    else if(dy>60 && dy>Math.abs(dx)*1.2){ swipeAt = Date.now(); if(full) closeGallery(); else { state.gx = null; renderAll(); } }
  }, {passive:true});
  /* کپی متن (نشانی) */
  function copyText(txt){
    function ok(){ toast('نشانی کپی شد.', 'success'); }
    function fallback(){
      var ta = document.createElement('textarea'); ta.value = txt; ta.setAttribute('readonly',''); ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy') ? ok() : toast('کپی نشد؛ نشانی را دستی انتخاب کنید.', 'warn'); } catch (er) { toast('کپی نشد؛ نشانی را دستی انتخاب کنید.', 'warn'); }
      ta.remove();
    }
    try { navigator.clipboard.writeText(txt).then(ok, fallback); } catch (er) { fallback(); }
  }
  /* کلیک روی تصویر کوچک، دکمه‌های گالری و نشانی: کارت پشتشان انتخاب نمی‌شود */
  document.addEventListener('click', function(e){
    var t = e.target.closest && e.target.closest('[data-gal],[data-gstep],[data-gmin],[data-gfull],[data-copy]');
    if(!t) return;
    e.stopPropagation(); e.preventDefault();
    if(t.hasAttribute('data-copy')){ copyText(t.getAttribute('data-copy')); return; }
    if(t.hasAttribute('data-gal')){
      var k = t.getAttribute('data-gal');
      state.gx = (state.gx && state.gx.key===k) ? null : {key:k, pid:t.getAttribute('data-gp'), cat:t.getAttribute('data-gc'), i:0};
      renderAll();
      var gv = document.querySelector('.gview'); if(gv) gv.scrollIntoView({block:'nearest', behavior:reduced?'auto':'smooth'});
      return;
    }
    if(t.hasAttribute('data-gmin')){ state.gx = null; renderAll(); return; }
    if(t.hasAttribute('data-gstep')){ gStep(+t.getAttribute('data-gstep')); return; }
    if(t.hasAttribute('data-gfull') && Date.now()-swipeAt>400) openGallery();
  }, true);
  document.addEventListener('keydown', function(e){
    if(e.key!=='Enter' && e.key!==' ') return;
    var t = e.target.closest && e.target.closest('[data-gal],[data-gfull],[data-copy]');
    if(t && t.getAttribute('role')==='button'){ e.preventDefault(); t.click(); }
  });

  /* ---------- گزارش فروشگاه ---------- */
  var REPORT_REASONS = ['قیمت اشتباه', 'ناموجود', 'محصول متفاوت', 'فریب در فروش', 'پیگیری بعد از خرید', 'اطلاعات یا هزینه ارسال اشتباه', 'تفاوت قیمت سایت و ترب', 'سایر'];
  var repDlg = $('#reportDlg'), repSid = null;
  $('#repOpts').innerHTML = REPORT_REASONS.map(function(r, i){
    return '<label class="rep-opt"><input type="radio" name="repReason" value="'+i+'"><span>'+r+'</span></label>';
  }).join('');
  $('#repFollow').href = LINKS.guarantee;
  function repSync(){
    var n = $('#repText').value.length;
    $('#repCnt').textContent = '('+fa(n)+' / ۴۰۰)';
    $('#repSend').disabled = !repDlg.querySelector('input[name="repReason"]:checked');
  }
  function openReport(sid){
    var st = STORES[sid]; if(!st) return;
    repSid = sid; $('#repForm').reset(); $('#repStore').textContent = st.name; repSync();
    if(typeof repDlg.showModal==='function') repDlg.showModal(); else repDlg.setAttribute('open','');
  }
  $('#repForm').addEventListener('input', repSync);
  $('#repForm').addEventListener('change', repSync);
  $('#repClose').addEventListener('click', function(){ repDlg.close(); });
  $('#repCancel').addEventListener('click', function(){ repDlg.close(); });
  repDlg.addEventListener('click', function(e){ if(e.target===repDlg) repDlg.close(); });
  $('#repForm').addEventListener('submit', function(e){
    e.preventDefault();
    var c = repDlg.querySelector('input[name="repReason"]:checked'); if(!c) return;
    repDlg.close();
    toast('گزارش «'+REPORT_REASONS[+c.value]+'» دربارهٔ «'+STORES[repSid].name+'» ثبت شد. ممنون که خبر دادید.', 'success');
  });

  /* ---------- جستجو در محدودهٔ دلخواه روی نقشه ---------- */
  var areaBtn = $('#areaBtn'), quietMapUntil = 0;
  function quietMap(){ quietMapUntil = Date.now() + 1500; }
  function onMapMoved(){
    if(Date.now() < quietMapUntil || state.tab!=='results' || stage()==='none' || stage()==='dir') return;
    areaBtn.innerHTML = IC.pin + '<span>' + (state.filters.area ? 'جستجو در محدودهٔ جدید' : 'جستجو در این محدوده') + '</span>';
    areaBtn.hidden = false;
  }
  areaBtn.addEventListener('click', function(){
    state.filters.area = MapView.getBounds(); areaBtn.hidden = true;
    afterFilterChange();
    toast(offerRows().length ? 'فقط فروشگاه‌های داخل این محدوده نمایش داده می‌شوند.' : 'در این محدوده فروشگاهی پیدا نشد؛ نقشه را جابه‌جا کنید یا فیلتر محدوده را بردارید.', offerRows().length ? 'info' : 'warn');
  });

  /* ---------- جمع کردن بخش بالا (دسکتاپ: از جستجو تا مرتب‌سازی · موبایل: جستجوی بسته) ---------- */
  var appEl = $('.app'), topEl = $('.top'), listEl = $('#list'), mqMobile = window.matchMedia('(max-width:859px)'), mqTablet = window.matchMedia('(min-width:600px) and (max-width:859px)');
  var topMin = false, minBtn = $('#minBtn'), searchSel = $('#searchSel');
  function isMobile(){ return mqMobile.matches; }
  function setTopMin(on){
    topMin = !!on;
    appEl.classList.toggle('top-min', topMin);
    var lbl = topMin ? 'باز کردن بخش بالا' : 'جمع کردن بخش بالا';
    minBtn.setAttribute('aria-expanded', String(!topMin)); minBtn.setAttribute('aria-label', lbl); minBtn.title = lbl;
    renderSearchSel();
  }
  /* موبایل، جستجوی بسته: اگر محصولی انتخاب شده، نامش در جستجو می‌ماند */
  function renderSearchSel(){
    var p = curProd(), on = isMobile() && topMin && !!p && state.tab==='results';
    searchSel.hidden = !on; $('#searchForm').classList.toggle('has-sel', on);
    if(on && searchSel.textContent!==p.title) searchSel.textContent = p.title;
  }
  minBtn.addEventListener('click', function(){ setTopMin(!topMin); });
  $('#minShade').addEventListener('click', function(){ setTopMin(false); });
  searchSel.addEventListener('click', function(){ setTopMin(false); qEl.focus(); qEl.select(); });
  /* موبایل: لمس نقشه یا فهرست، جستجوی باز را می‌بندد */
  document.addEventListener('pointerdown', function(e){
    if(!isMobile() || topMin || e.target.closest('.top, dialog, .tip')) return;
    qEl.blur(); setTopMin(true);
  });

  /* ---------- موبایل: صفحهٔ پایین کشیدنی (full / half / peek) روی نقشهٔ تمام‌صفحه ---------- */
  var sheet = 'full', peekH = 96, gripEl = $('#sheetGrip'), peekEl = $('#sheetPeek'), toastEl = $('#toast');
  function autoSheet(){
    if(state.tab==='plan') return state.planSel ? 'full' : 'half';
    var st0 = stage();
    if(st0==='dir') return state.selected ? 'full' : 'half';
    if(st0==='none') return 'peek';
    if(st0!=='stores') return 'full';
    return state.selected ? 'full' : 'half';
  }
  function snapY(mode){
    var h = listEl.offsetHeight;
    return mode==='full' ? 0 : mode==='half' ? Math.round(h*.5) : Math.max(0, h-peekH);
  }
  /* بخشی از نقشه که زیر نوار بالا و صفحهٔ پایین نمی‌رود (برای جاگیری پین‌ها) */
  function syncInsets(){
    if(!isMobile()){ MapView.setInsets({t:0, b:0}); appEl.style.removeProperty('--sheet-vis'); return; }
    if(mqTablet.matches){ MapView.setInsets({t: topEl.offsetHeight, b: viewsEl.offsetHeight, r: listEl.offsetWidth + 12}); }   // تبلت: فهرست کنار نقشه است
    else { var vis = sheet==='peek' ? peekH : listEl.offsetHeight - snapY('half'); MapView.setInsets({t: topEl.offsetHeight, b: vis + viewsEl.offsetHeight}); }
    appEl.style.setProperty('--sheet-vis', (listEl.offsetHeight - snapY(sheet))+'px');
  }
  function setSheet(mode, keepScroll){
    if(!isMobile()) return;
    if(view!=='map'){ sheet = mode; return; }   // صفحهٔ پایین فقط در صفحهٔ نقشه است
    sheet = mode; appEl.setAttribute('data-sheet', mode);
    if(mode==='peek'){ renderPeek(); peekH = gripEl.offsetHeight + peekEl.offsetHeight + 14; }
    listEl.style.setProperty('--sy', snapY(mode)+'px');
    if(mode==='peek' || (mode==='half' && !keepScroll)) listEl.scrollTop = 0;
    syncInsets();
  }
  /* نوار خلاصه وقتی صفحه پایین است: نام فروشگاهِ انتخاب‌شده یا خلاصهٔ نتایج */
  var lastPeek = '';
  function renderPeek(){
    if(!isMobile()) return;
    var html, sel = state.tab==='plan' ? state.planSel : (!state.compare && state.selected), o = sel && state.tab==='results' ? offer(sel) : null;
    if(o) html = '<span class="pk-t"><b>'+esc(o.store.name)+'</b><small>'+fa(o.price)+' تومان · '+fa1(o.km)+' کیلومتر · '+etaHTML(o.km,o.sid)+'</small></span>';
    else if(sel && STORES[sel]) html = '<span class="pk-t"><b>'+esc(STORES[sel].name)+'</b><small>'+(state.tab==='plan' ? 'برنامهٔ سر زدن' : fa1(roadKm(state.origin, STORES[sel]))+' کیلومتر · '+esc(STORES[sel].addr))+'</small></span>';
    else html = '<span class="pk-t"><small>'+(state.tab==='plan' ? $('#planSummary').innerHTML : $('#summary').innerHTML)+'</small></span>';
    html += '<span class="pk-go">'+ICON.up+'</span>';
    if(html!==lastPeek){ peekEl.innerHTML = html; lastPeek = html; }
    peekEl.setAttribute('aria-label', 'بالا آوردن فهرست: '+peekEl.textContent);
  }
  /* زدن روی نوار خلاصه: اگر فروشگاهی انتخاب شده، تمام‌صفحه و پرش به همان کارت در فهرست */
  peekEl.addEventListener('click', function(){
    var sel = state.tab==='plan' ? state.planSel : (!state.compare && state.selected);
    if(!sel){ setSheet('half'); return; }
    setSheet('full', true);
    requestAnimationFrame(function(){
      var el = (state.tab==='plan' ? planList.querySelector('.pcard[data-sid="'+sel+'"]') : cardsEl.querySelector('.card[data-sid="'+sel+'"]'));
      if(el) el.scrollIntoView({block:'start'});
    });
  });
  function gripTap(){ setSheet(sheet==='half' ? 'full' : 'half'); }
  gripEl.addEventListener('click', gripTap);
  gripEl.addEventListener('keydown', function(e){
    if(e.key==='Enter' || e.key===' '){ e.preventDefault(); gripTap(); }
    else if(e.key==='ArrowUp'){ e.preventDefault(); setSheet(sheet==='peek' ? 'half' : 'full'); }
    else if(e.key==='ArrowDown'){ e.preventDefault(); setSheet(sheet==='full' ? 'half' : 'peek'); }
  });

  /* کشیدن: در حالت half/peek هر کشیدن عمودی صفحه را جابه‌جا می‌کند (کشیدن فهرست رو به بالا = تمام‌صفحه)؛
     در حالت full فقط وقتی صفحه تا بالا اسکرول شده و رو به پایین کشیده شود. */
  var drag = null;
  function curY(){ return parseFloat(listEl.style.getPropertyValue('--sy')) || 0; }
  function dragStart(x, y, target){
    drag = {x0:x, y0:y, sy0:curY(), on:false, decided:false, native:false, ly:y, lt:Date.now(), v:0};
  }
  function grab(y){ drag.on = true; drag.native = false; drag.y0 = y; drag.sy0 = curY(); listEl.classList.add('dragging'); }
  function dragMove(x, y){
    if(!drag) return false;
    var dx = x-drag.x0, dy = y-drag.y0;
    if(!drag.decided){
      if(Math.abs(dx)<6 && Math.abs(dy)<6) return false;
      drag.decided = true;
      if(Math.abs(dx)>Math.abs(dy)){ drag = null; return false; }   // کشیدن افقی (چیپ‌ها، گالری)
      if(sheet==='full' && (dy<0 || listEl.scrollTop>0)) drag.native = true;   // اسکرول معمولی فهرست
      else grab(y);
    }
    /* اسکرول معمولی تا بالای فهرست رسید و کاربر همچنان رو به پایین می‌کشد ← از همین‌جا صفحه پایین می‌آید */
    if(drag.native){
      if(listEl.scrollTop<=0 && y>drag.ly) grab(y);
      else { drag.ly = y; drag.lt = Date.now(); return false; }
    }
    if(!drag.on) return false;
    var now = Date.now(), max = listEl.offsetHeight - peekH;
    if(now>drag.lt) drag.v = (y-drag.ly)/(now-drag.lt);
    drag.ly = y; drag.lt = now;
    var ny = drag.sy0 + (y-drag.y0);
    if(ny<0) ny = ny/3; else if(ny>max) ny = max + (ny-max)/3;   // کمی کش آمدن در دو سر
    listEl.style.setProperty('--sy', ny+'px');
    return true;
  }
  function dragEnd(){
    if(!drag) return false;
    var d = drag; drag = null;
    if(!d.on) return false;
    listEl.classList.remove('dragging');
    var y = curY(), order = ['full','half','peek'], i;
    if(Math.abs(d.v)>.45) i = order.indexOf(sheet) + (d.v>0 ? 1 : -1);
    else i = order.map(function(m){ return Math.abs(snapY(m)-y); }).reduce(function(b, v, k, a){ return v<a[b] ? k : b; }, 0);
    setSheet(order[clamp(i, 0, 2)]);
    return true;
  }
  listEl.addEventListener('touchstart', function(e){
    if(!isMobile() || view!=='map' || e.touches.length>1 || e.target.closest('input,select,textarea')) return;
    dragStart(e.touches[0].clientX, e.touches[0].clientY, e.target);
  }, {passive:true});
  listEl.addEventListener('touchmove', function(e){
    if(drag && dragMove(e.touches[0].clientX, e.touches[0].clientY) && e.cancelable) e.preventDefault();
  }, {passive:false});
  listEl.addEventListener('touchend', function(e){ if(dragEnd() && e.cancelable) e.preventDefault(); });
  listEl.addEventListener('touchcancel', dragEnd);
  /* موس (برای آزمایش روی دسکتاپ با پنجرهٔ باریک): از دستگیره یا نوار خلاصه بکشید */
  [gripEl, peekEl].forEach(function(el){
    el.addEventListener('pointerdown', function(e){
      if(!isMobile() || e.pointerType!=='mouse') return;
      dragStart(e.clientX, e.clientY, el); drag.decided = true; drag.on = true; listEl.classList.add('dragging');
      var moved = false;
      function mv(ev){ moved = true; dragMove(ev.clientX, ev.clientY); }
      function up(){
        window.removeEventListener('pointermove', mv); window.removeEventListener('pointerup', up);
        if(moved){ dragEnd(); el.addEventListener('click', function stop(ev){ ev.stopImmediatePropagation(); el.removeEventListener('click', stop, true); }, true); }
        else { drag = null; listEl.classList.remove('dragging'); }
      }
      window.addEventListener('pointermove', mv); window.addEventListener('pointerup', up);
    });
  });
  /* چرخ موس: روی صفحهٔ نیمه‌باز رو به پایین ← تمام‌صفحه؛ بالای فهرست و باز هم رو به بالا ← صفحه پایین می‌آید */
  var pull = 0, pullT = 0;
  listEl.addEventListener('wheel', function(e){
    if(!isMobile() || view!=='map') return;
    if(sheet!=='full'){ if(e.deltaY>0){ e.preventDefault(); setSheet('full'); } return; }
    if(e.deltaY<0 && listEl.scrollTop<=0){
      var now = Date.now(); if(now-pullT>300) pull = 0; pullT = now;
      pull -= e.deltaY;
      if(pull>160){ pull = 0; setSheet('half'); }
    } else pull = 0;
  }, {passive:false});

  /* تغییر اندازهٔ نوار بالا یا پنجره: موقعیت صفحهٔ پایین دوباره حساب شود */
  function syncLayout(){
    appEl.style.setProperty('--top-h', topEl.offsetHeight+'px');
    if(isMobile()){ listEl.classList.add('dragging'); setSheet(sheet); requestAnimationFrame(function(){ listEl.classList.remove('dragging'); }); }
  }
  if('ResizeObserver' in window) new ResizeObserver(syncLayout).observe(topEl);
  window.addEventListener('resize', syncLayout);
  function applyLayout(){
    var m = isMobile();
    /* توست داخل نقشه است؛ روی موبایل باید بالای صفحهٔ پایین دیده شود */
    if(m && toastEl.parentNode!==document.body) document.body.appendChild(toastEl);
    else if(!m && toastEl.parentNode===document.body) $('#map').appendChild(toastEl);
    if(m){ setTopMin(true); sheet = autoSheet(); if(view!=='map') appEl.removeAttribute('data-sheet'); syncLayout(); }
    else { appEl.removeAttribute('data-sheet'); listEl.style.removeProperty('--sy'); setTopMin(false); syncInsets(); }
    renderAll();
  }
  if(mqMobile.addEventListener) mqMobile.addEventListener('change', applyLayout); else mqMobile.addListener(applyLayout);


  /* ---------- سه صفحه: فهرست / نقشه / دستیار (با #list، #map، #agent در آدرس؛ دکمهٔ بازگشت مرورگر هم کار می‌کند) ---------- */
  var VIEWS = {list:1, map:1, agent:1, inq:1}, viewsEl = $('#views');
  $('#vtList').innerHTML = IC.list; $('#vtMap').innerHTML = IC.map; $('#vtInq').innerHTML = IC.inquiry;
  function viewFromHash(){ var h = location.hash.replace('#',''); return VIEWS[h] ? h : 'agent'; }   // صفحهٔ اول: تربچت
  function applyView(v, opt){
    opt = opt || {};
    if(v===view && appEl.hasAttribute('data-view')) return;
    if(view==='agent' && v!=='agent') NQ.AgentUI.onHide();
    view = v; appEl.setAttribute('data-view', v);
    Array.prototype.forEach.call(viewsEl.querySelectorAll('.view-tab'), function(a){
      var on = a.getAttribute('data-view')===v;
      if(on) a.setAttribute('aria-current','page'); else a.removeAttribute('aria-current');
    });
    if(v==='map'){
      MapView.refresh();   // نقشه پنهان بوده؛ اندازه‌اش دوباره خوانده شود
      if(isMobile()){ var keep = sheet; sheet = ''; setSheet(opt.noFit ? 'peek' : (keep || autoSheet())); }
      if(!opt.noFit) fitCurrent();
    } else appEl.removeAttribute('data-sheet');
    syncLayout(); renderAll();
    if(v==='agent') NQ.AgentUI.onShow();
    if(v==='inq') renderInqs(true);
  }
  function goView(v, opt){
    if(v===view) return;
    try { history.pushState(null, '', '#'+v); } catch (e) { location.hash = v; }
    applyView(v, opt);
  }
  viewsEl.addEventListener('click', function(e){
    var a = e.target.closest('[data-view]'); if(!a) return;
    e.preventDefault(); goView(a.getAttribute('data-view'));
  });
  window.addEventListener('popstate', function(){ applyView(viewFromHash()); });
  window.addEventListener('hashchange', function(){ applyView(viewFromHash()); });

  /* ---------- استعلام‌ها: قیمت و موجودی‌ای که ترب از فروشنده پرسیده ----------
     هر استعلام: {id, sid, cat, title, at, status: pending | answered | noreply, answer:{price, stock, note, at}, seen}
     فعلاً پاسخ فروشنده شبیه‌سازی می‌شود (چند ثانیه بعد)؛ در نسخهٔ واقعی از سرویس استعلام ترب می‌آید. */
  var INQ_KEY = 'nq-inq-v1', inqs = [], iqFilter = 'all';
  var INQ_NOTES = ['همهٔ رنگ‌ها موجود است.', 'تا ساعت ۲۰ در فروشگاه هستیم؛ قبل از آمدن تماس بگیرید.', 'با گارانتی ۱۸ ماهه و فاکتور رسمی.', 'برای رزرو تا فردا نگه می‌داریم.', 'فقط رنگ مشکی مانده است.'];
  function offerRow(cat, sid, title){ return (OFFERS[cat]||[]).filter(function(r){ return r[0]===sid && (!title || r[1]===title); })[0]; }
  function hashN(t){ var h = 0; String(t).split('').forEach(function(c){ h = (h*31 + c.charCodeAt(0)) >>> 0; }); return h; }
  /* کالای استعلام: اگر پنجرهٔ فروشگاه باز است همان کالا، وگرنه کالای انتخاب‌شده در فهرست */
  function inqContext(sid){
    if(storeDlg.open && sdlg && sdlg.sid===sid && sdlg.cat){ var r0 = offerRow(sdlg.cat, sid, sdlg.title); return {cat: sdlg.cat, title: r0 ? r0[1] : sdlg.title}; }
    var o = offer(sid); if(o) return {cat: state.cat, title: o.title};
    var cat = Object.keys(OFFERS).filter(function(c){ return offerRow(c, sid); })[0], r = cat && offerRow(cat, sid);
    return {cat: cat || null, title: r ? r[1] : ''};
  }
  function answerFor(q){
    var r = offerRow(q.cat, q.sid, q.title), h = hashN(q.id);
    var price = r ? Math.round(r[3]*(1 + ((h % 7) - 3)/100)/1000)*1000 : 0;
    return {price: price, stock: h % 6 === 0 ? 'out' : 'in', note: INQ_NOTES[h % INQ_NOTES.length], at: Date.now()};
  }
  function saveInqs(){ try { localStorage.setItem(INQ_KEY, JSON.stringify(inqs)); } catch (e) {} }
  function loadInqs(){
    var d = null; try { d = JSON.parse(localStorage.getItem(INQ_KEY) || 'null'); } catch (e) {}
    if(!d){   // نمونه برای اولین بار، تا صفحه خالی نباشد
      var now = Date.now();
      d = [['s9','headphone',26],['s13','laptop',3],['s2','keyboard',.8]].map(function(x, i){
        var r = offerRow(x[1], x[0]), q = {id: 'q'+(now-i), sid: x[0], cat: x[1], title: r ? r[1] : '', at: now - x[2]*3600e3, status: i===2 ? 'noreply' : 'answered', seen: true, demo: true};
        if(q.status==='answered'){ q.answer = answerFor(q); q.answer.at = q.at + 14*60e3; }
        return q;
      });
    }
    inqs = d;
    inqs.forEach(function(q){ if(q.store && !STORES[q.sid]) STORES[q.sid] = q.store; });   // فروشگاه‌های واقعی کاتالوگ (از تربچت)
    inqs.forEach(function(q){ if(q.status==='pending' && !q.remote) scheduleInq(q, Date.now()-q.at > 15000 ? 600 : 0); });
    saveInqs();
  }
  function scheduleInq(q, delay){ setTimeout(function(){ answerInq(q.id); }, delay || 7000 + (hashN(q.id) % 6000)); }
  function createInq(sid, cat, title){
    var q = {id: 'q'+Date.now(), sid: sid, cat: cat, title: title || '', at: Date.now(), status: 'pending', seen: true};
    if(STORES[sid] && STORES[sid].real) q.store = STORES[sid];
    inqs.unshift(q); saveInqs(); renderInqs();
    /* استعلام واقعی: از طریق بک‌اند ترب به اپ فروشنده می‌رود؛ اگر بک‌اند در دسترس نبود، شبیه‌سازی (با برچسب «نمونه») */
    var r = offerRow(cat, sid, title);
    var sent = NQ.Backend && NQ.Backend.sendInquiry(q, {shopName: STORES[sid] && STORES[sid].name, price: r ? r[3] : 0});
    if(sent) sent.then(function(ok){ if(!ok){ q.demo = true; saveInqs(); renderInqs(); scheduleInq(q); } });
    else { q.demo = true; scheduleInq(q); }
    return q;
  }
  /* به‌روزرسانی استعلام‌ها با پاسخ واقعی فروشنده (از بک‌اند) */
  NQ.Inq = {
    list: function(){ return inqs; },
    save: function(){ saveInqs(); },
    create: function(sid, cat, title){ return createInq(sid, cat, title); },
    applyRemote: function(q, patch, toastMsg){
      var was = q.status;
      Object.keys(patch).forEach(function(k){ q[k] = patch[k]; });
      if(q.status!==was) q.seen = view==='inq';
      saveInqs(); renderInqs();
      if(q.status==='answered' && was!=='answered') toast('«'+((STORES[q.sid]||{}).name||'فروشنده')+'» به استعلام'+(q.title ? ' «'+modelOf(q.title)+'»' : '')+' جواب داد.', 'success');
    }
  };
  function answerInq(id){
    var q = inqs.filter(function(x){ return x.id===id; })[0]; if(!q || q.status!=='pending') return;
    q.status = 'answered'; q.answer = answerFor(q); q.seen = view==='inq';
    saveInqs(); renderInqs();
    toast('«'+STORES[q.sid].name+'» به استعلام'+(q.title ? ' «'+modelOf(q.title)+'»' : '')+' جواب داد.', 'success');
  }
  function agoTxt(t){ var m = Math.round((Date.now()-t)/60000); return m<1 ? 'همین الان' : m<60 ? fa(m)+' دقیقه پیش' : m<1440 ? fa(Math.round(m/60))+' ساعت پیش' : fa(Math.round(m/1440))+' روز پیش'; }
  var IQ_ST = {pending:'در انتظار پاسخ', answered:'پاسخ داده شد', noreply:'بدون پاسخ'};
  /* پاسخ استعلام تا مدتی معتبر است و در این مدت دوباره پرسیده نمی‌شود (مگر خود کاربر تماس بگیرد) */
  var INQ_VALID = 24*3600e3;
  function inqValid(q){ return q.status==='answered' && q.answer && Date.now() - q.answer.at < INQ_VALID; }
  function leftTxt(ms){ return ms>=3600e3 ? fa(Math.ceil(ms/3600e3))+' ساعت' : fa(Math.max(1, Math.ceil(ms/60000)))+' دقیقه'; }
  /* رنگ نشان: پاسخ «ناموجود» زرد، پاسخ منقضی خاکستری */
  function inqBadge(q){
    if(q.status==='answered' && !inqValid(q)) return {cls: 'expired', label: 'منقضی شده'};
    if(q.status==='answered' && q.answer && q.answer.stock==='out') return {cls: 'answered out', label: IQ_ST.answered};
    return {cls: q.status, label: IQ_ST[q.status]};
  }
  function inqCardHTML(q){
    var st = STORES[q.sid], r = offerRow(q.cat, q.sid, q.title), a = q.answer;
    var body;
    if(q.status==='answered' && a){
      var ok = inqValid(q);
      body = '<div class="iq-ans'+(ok ? '' : ' old')+'"><div class="iq-price"><span>قیمت اعلام‌شده</span><b>'+fa(a.price)+' <small>تومان</small></b></div>' +
          '<span class="stock '+a.stock+'">'+(a.stock==='in' ? 'موجود است' : 'فعلاً موجود نیست')+'</span>' +
        '<p class="iq-note">«'+esc(a.note)+'» <small>— فروشنده، '+agoTxt(a.at)+'</small></p>' +
        '<p class="iq-valid">'+(ok ? 'این پاسخ تا '+leftTxt(a.at + INQ_VALID - Date.now())+' دیگر معتبر است.' : 'اعتبار این پاسخ تمام شده؛ قیمت و موجودی ممکن است عوض شده باشد. برای پاسخ تازه، از اطلاعات فروشگاه دوباره استعلام بگیرید.')+'</p></div>';
    } else if(q.status==='pending'){
      body = '<div class="iq-wait"><i class="iq-bar"></i><span>ترب در حال پرسیدن از فروشنده است؛ معمولاً تا ۲۰ دقیقه.</span></div>';
    } else body = '<div class="iq-wait no"><span>فروشنده هنوز جواب نداده؛ می‌توانید خودتان تماس بگیرید.</span></div>';
    var bd = inqBadge(q);
    return '<li class="iq-card st-'+q.status+(bd.cls==='expired' ? ' expired' : '')+(q.seen ? '' : ' new')+'">' +
      '<div class="iq-top"><span class="iq-art" aria-hidden="true">'+storeArtHTML(q.sid)+'</span>' +
        '<button type="button" class="iq-t" data-iq-store="'+q.id+'"><b>'+esc(st.name)+'</b><small>'+esc(q.title || (catById(q.cat)||{}).name || '')+'</small></button>' +
        '<span class="iq-badge '+bd.cls+'">'+bd.label+'</span></div>' + body +
      '<div class="iq-foot"><span class="iq-time">ثبت '+agoTxt(q.at)+(q.demo ? ' · نمونه' : '')+(q.track ? ' · کد پیگیری '+esc(q.track) : '')+'</span><div class="iq-acts">' +
        '<button type="button" class="act wa" data-call="'+q.sid+'" aria-label="تماس با فروشگاه" data-hint="تماس با فروشگاه">'+IC.phone+'</button>' +
        '<button type="button" class="act wa" data-iq-map="'+q.id+'" aria-label="روی نقشه" data-hint="روی نقشه">'+IC.map+'</button>' +
        (q.cat ? '<button type="button" class="act wa" data-iq-plan="'+q.id+'" aria-pressed="'+Plan.has(q.sid, q.cat)+'" aria-label="سر زدن" data-hint="'+(Plan.has(q.sid, q.cat) ? 'در سر زدن‌ها' : 'افزودن به سر زدن‌ها')+'">'+IC.bookmark+'</button>' : '') +
        '<button type="button" class="act wa" data-iq-rm="'+q.id+'" aria-label="حذف استعلام" data-hint="حذف">'+ICON.rm+'</button>' +
      '</div></div></li>';
  }
  function renderInqs(markSeen){
    var unseen = inqs.filter(function(q){ return !q.seen && q.status==='answered'; }).length;
    if(markSeen && view==='inq' && unseen){ inqs.forEach(function(q){ q.seen = true; }); saveInqs(); unseen = 0; }
    var b = $('#inqBadge'); b.hidden = !unseen; b.textContent = fa(unseen);
    if(view!=='inq') return;
    var cnt = {all: inqs.length, pending: 0, answered: 0, noreply: 0};
    inqs.forEach(function(q){ cnt[q.status]++; });
    Array.prototype.forEach.call(document.querySelectorAll('#iqSeg button'), function(x){
      var k = x.getAttribute('data-iq'); x.setAttribute('aria-checked', String(k===iqFilter)); x.querySelector('small').textContent = fa(cnt[k]||0);
    });
    var list = inqs.filter(function(q){ return iqFilter==='all' || q.status===iqFilter; });
    $('#iqList').innerHTML = list.length ? list.map(inqCardHTML).join('') :
      '<li class="empty">'+(inqs.length ? 'استعلامی در این دسته نیست.' : 'هنوز استعلامی نگرفته‌اید. در اطلاعات هر فروشگاه «استعلام قیمت» ← «ترب برایم استعلام بگیرد» را بزنید.')+'</li>';
  }
  $('#iqSeg').addEventListener('click', function(e){ var x = e.target.closest('[data-iq]'); if(!x) return; iqFilter = x.getAttribute('data-iq'); renderInqs(); });
  $('#iqList').addEventListener('click', function(e){
    var t, q = function(a){ return inqs.filter(function(x){ return x.id===t.getAttribute(a); })[0]; };
    if((t = e.target.closest('[data-call]'))){ callStore(t.getAttribute('data-call')); return; }
    if((t = e.target.closest('[data-iq-store]'))){ var a = q('data-iq-store'); openStoreDlg(a.sid, a.cat, a.title); return; }
    if((t = e.target.closest('[data-iq-map]'))){ var m = q('data-iq-map'); if(m.cat) openStoreFrom(m.cat, m.sid, m.title, 'map'); else storeOnMap(m.sid); return; }
    if((t = e.target.closest('[data-iq-plan]'))){ var pl = q('data-iq-plan'); var on = Plan.toggle(pl.sid, pl.cat); toast(on ? 'به سر زدن‌ها اضافه شد.' : 'از سر زدن‌ها برداشته شد.', on ? 'success' : 'info'); renderAll(); renderInqs(); return; }
    if((t = e.target.closest('[data-iq-rm]'))){ var id = t.getAttribute('data-iq-rm'); inqs = inqs.filter(function(x){ return x.id!==id; }); saveInqs(); renderInqs(); }
  });
  loadInqs();

  /* ---------- پیشنهاد نهایی بر اساس سؤال‌های تربچت (بودجه، برند، رفت‌وآمد، نزدیکی) ----------
     w: {cat, budget:{min,max}, brands:[...], mode, maxMin, nearKm}. اگر با همهٔ شرط‌ها چیزی نماند، کمی شل‌تر می‌گیرد. */
  function chatPriceRange(cat){
    var ps = (OFFERS[cat]||[]).filter(function(r){ return r[4]!=='out'; }).map(function(r){ return r[3]; });
    if(!ps.length) return {lo: 0, hi: 1e6, step: 1e5};
    var lo = Math.min.apply(null, ps), hi = Math.max.apply(null, ps), step = hi>2e7 ? 1e6 : hi>2e6 ? 1e5 : 1e4;
    lo = Math.floor(lo/step)*step; hi = Math.ceil(hi/step)*step; if(hi-lo<step*2) hi = lo+step*2;
    return {lo: lo, hi: hi, step: step};
  }
  function chatBrands(cat){
    var m = {};
    (PRODS[cat]||[]).forEach(function(p){
      var s = prodStats(p, cat, true), b = p.brand || shortOf(p.title).split(' ')[0];
      if(!m[b]) m[b] = {brand: b, logo: NQ.brandLogo(b), models: 0, min: 0};
      m[b].models++; if(s.min && (!m[b].min || s.min<m[b].min)) m[b].min = s.min;
    });
    return Object.keys(m).map(function(k){ return m[k]; });
  }
  function modeOf(w, km){ return w.mode && w.mode!=='auto' ? w.mode : Travel.suggest(km); }
  function recommend(w){
    var rows = (OFFERS[w.cat]||[]).map(function(r){ return mk(r, w.cat); }).filter(function(o){ return o.stock!=='out'; });
    rows.forEach(function(o){ o.tmode = modeOf(w, o.km); o.tmin = Travel.minutes(o.tmode, o.km); });
    function ok(o, k){
      var b = w.budget || {};
      if(b.max && o.price > b.max*k) return false;
      if(b.min && o.price < b.min/k) return false;
      if(w.brands && w.brands.length && w.brands.indexOf(o.brand)<0) return false;
      if(w.maxMin && o.tmin > w.maxMin*k) return false;
      if(w.nearKm && o.km > w.nearKm*k) return false;
      return true;
    }
    var res = rows.filter(function(o){ return ok(o, 1); }), relaxed = false;
    if(!res.length){ res = rows.filter(function(o){ return ok(o, 1.35); }); relaxed = true; }
    if(!res.length && w.brands && w.brands.length){ res = rows.filter(function(o){ var b = w.brands; w.brands = []; var r = ok(o, 1.35); w.brands = b; return r; }); relaxed = true; }
    var min = Math.min.apply(null, res.map(function(o){ return o.price; })) || 1;
    var wNear = w.nearKm ? .22 : .03, wTime = w.maxMin ? .015 : 0;
    res.sort(function(a, b){
      function sc(o){ return o.price/min + (1-(o.store.trust==null?.8:o.store.trust))*.35 - (o.store.guarantee?.15:0) - (o.store.torobpay?.1:0) + (o.stock==='unsure'?.12:0) + o.km*wNear + o.tmin*wTime; }
      return sc(a)-sc(b);
    });
    return {offers: res, total: rows.length, relaxed: relaxed};
  }
  function etaModeHTML(km, mode){ return '<span class="eta" title="'+Travel.label(mode)+'">'+IC[mode]+'<span>'+fa(Travel.minutes(mode, km))+' دقیقه</span></span>'; }

  /* ---------- مقایسهٔ چند فروشگاه (از پیشنهادهای تربچت) ---------- */
  function offerCmpData(list, mode){
    var cols = list.map(function(x){ var r = offerRow(x.cat, x.sid, x.title); return r ? mk(r, x.cat) : null; }).filter(Boolean);
    var M = cols.map(function(o){ return mode && mode!=='auto' ? mode : Travel.suggest(o.km); });
    var rows = [
      {l:'محصول', v:cols.map(function(o){ return modelOf(o.title); })},
      {l:'قیمت', v:cols.map(function(o){ return fa(o.price)+' تومان'; }), win:winners(cols.map(function(o){return o.price}), true)},
      {l:'موجودی', v:cols.map(function(o){ return STOCK[o.stock]; })},
      {l:'فاصله', v:cols.map(function(o){ return fa1(o.km)+' کیلومتر'; }), win:winners(cols.map(function(o){return o.km}), true)},
      {l:'زمان رسیدن', v:cols.map(function(o, i){ return fa(Travel.minutes(M[i], o.km))+' دقیقه با '+Travel.label(M[i]); }), win:winners(cols.map(function(o, i){ return Travel.minutes(M[i], o.km); }), true)},
      {l:'امتیاز فروشگاه', v:cols.map(function(o){ return o.store.rating ? '★ '+fa1(o.store.rating)+' ('+fa(o.store.years)+' سال)' : '—'; }), win:winners(cols.map(function(o){return o.store.rating||0}), false)},
      {l:'ضمانت ترب', v:cols.map(function(o){ return o.store.guarantee ? 'دارد' : 'ندارد'; })},
      {l:'پرداخت', v:cols.map(function(o){ return [o.store.torobpay ? 'ترب‌پی' : '', (o.store.installments||[]).length ? 'قسطی' : '', 'نقدی'].filter(Boolean).join('، '); })},
      {l:'ساعت کار', v:cols.map(function(o){ return o.store.hours+' · '+storeStatus(o.store).short; })},
      {l:'ارسال فوری', v:cols.map(function(o){ return o.store.fast || '—'; })}
    ];
    rows.forEach(function(r){ r.diff = !allSame(r.v); });
    return {cols: cols.map(function(o){ return {sid: o.sid, name: o.store.name, art: storeArtHTML(o.sid), title: o.title, price: o.price}; }), rows: rows};
  }
  function openOfferCompare(list, mode){
    var d = offerCmpData(list, mode); if(d.cols.length<2) return;
    $('#cmpDlgTitle').textContent = 'مقایسهٔ '+fa(d.cols.length)+' فروشگاه';
    $('#cmpDlgBody').innerHTML = '<div class="fc-heads" style="--n:'+d.cols.length+'">' + d.cols.map(function(c, i){
        return '<div class="fc-h">'+nbHTML(i+1)+'<span class="fc-img">'+c.art+'</span><b class="fc-name">'+esc(c.name)+'</b></div>';
      }).join('') + '</div>' +
      cmpGridHTML(d.cols.map(function(c){ return {name: c.name, p: {title: c.name}}; }), d.rows, 'fc-grid') +
      '<p class="sp-note">ردیف‌های پررنگ با هم فرق دارند؛ سبز = بهترین.</p>';
    if(typeof cmpDlg.showModal==='function') cmpDlg.showModal(); else cmpDlg.setAttribute('open','');
    $('#cmpDlgBody').scrollTop = 0;
  }

  /* ---------- راهنمای رسیدن به فروشگاه: نشانه‌های نزدیک، جهت، ورودی ساختمان ---------- */
  var BEARS = ['شمال', 'شمال‌شرق', 'شرق', 'جنوب‌شرق', 'جنوب', 'جنوب‌غرب', 'غرب', 'شمال‌غرب'];
  function bearing(a, b){
    var y = (b.lng-a.lng)*Math.cos(a.lat*Math.PI/180), x = b.lat-a.lat;
    return BEARS[Math.round(((Math.atan2(y, x)*180/Math.PI)+360)%360/45)%8];
  }
  function meters(km){ return km<1 ? fa(Math.max(10, Math.round(km*100)*10))+' متر' : fa1(km)+' کیلومتر'; }
  function storeGuide(sid, level){
    var st = STORES[sid]; if(!st) return null;
    var marks = (NQ.LANDMARKS||[]).map(function(l){ return {name: l.name, kind: l.kind, lat: l.lat, lng: l.lng}; })
      .concat(Object.keys(STORES).filter(function(k){ return k!==sid; }).map(function(k){ return {name: STORES[k].name, kind: 'store', lat: STORES[k].lat, lng: STORES[k].lng}; }))
      .map(function(m){ m.d = NQ.geo.distanceKm(m, st); return m; }).filter(function(m){ return m.d<=.6; })
      .sort(function(a, b){ return (a.kind==='store') - (b.kind==='store') || a.d - b.d; }).slice(0, level>1 ? 5 : 3);
    var bits = [], ad = st.addr;
    [/(پاساژ|مجتمع|ساختمان|بازارچه)[^،(]*/, /طبقهٔ?\s*[^،(]*/, /واحد\s*[^،(]*/, /(غرفهٔ?|فروشگاه شمارهٔ)\s*[^،(]*/, /(نبش|روبه‌روی|بالاتر از|جنب|خروجی)\s*[^،(]*/].forEach(function(re){ var m = ad.match(re); if(m) bits.push(m[0].trim()); });
    var paren = ad.match(/\(([^)]+)\)/); if(paren) bits.push(paren[1]);
    var km = roadKm(state.origin, st), x = storeStatus(st);
    var lines = marks.map(function(m){ return meters(m.d)+' '+bearing(m, st)+'ِ «'+m.name+'»'; });
    var tips = [];
    if(level>1){
      if(marks[0]) tips.push('اگر به «'+marks[0].name+'» رسیدید، حدود '+meters(marks[0].d)+' به سمت '+bearing(marks[0], st)+' بروید.');
      if(bits.length) tips.push('ورودی: '+bits.join('، ')+'.');
      tips.push('دنبال تابلوی «'+st.name+'» بگردید'+(x.k==='closed' ? '؛ الان بسته است ('+x.text+').' : '.'));
      tips.push('باز هم پیدا نکردید؟ با فروشگاه تماس بگیرید ('+st.phones[0]+') یا موقعیتتان را به‌روز کنید تا مسیر دقیق‌تر شود.');
    }
    return {sid: sid, name: st.name, addr: st.addr, art: storeArtHTML(sid), bits: bits, level: level || 1,
      from: meters(km)+' '+bearing(state.origin, st)+'ِ شما', walk: Travel.minutes('walk', km), car: Travel.minutes('car', km),
      status: x.text, statusK: x.k, phone: st.phones[0], lines: lines, tips: tips, route: routeURL(st, Travel.resolve(km, sid)),
      lat: st.lat, lng: st.lng, origin: {lat: state.origin.lat, lng: state.origin.lng}, close: NQ.geo.distanceKm(state.origin, st) < 1,
      marks: marks.map(function(m){ return {lat: m.lat, lng: m.lng, kind: m.kind, name: m.name}; })};
  }

  /* ---------- رابط صفحهٔ دستیار (js/agent.js) با بقیهٔ برنامه ---------- */
  /* پیشنهاد فروشگاه‌های یک دسته (بدون فیلترهای صفحهٔ فهرست). sort: smart | price | near */
  function suggestOffers(cat, o){
    o = o || {};
    var rows = (OFFERS[cat]||[]).map(function(r){ return mk(r, cat); }).filter(function(x){
      return x.stock!=='out' && (!o.title || x.title===o.title) && (!o.guarantee || x.store.guarantee) && (!o.openNow || isOpenNow(x.store));
    });
    var min = Math.min.apply(null, rows.map(function(x){ return x.price; })) || 1;
    var key = {
      price: function(x){ return x.price; },
      near: function(x){ return x.km; },
      smart: function(x){ return x.price/min + (1-(x.store.trust==null?.8:x.store.trust))*.35 - (x.store.guarantee?.15:0) - (x.store.torobpay?.1:0) + Math.min(x.hrs,168)/168*.25 + (x.stock==='unsure'?.12:0) + x.km*.03; }
    }[o.sort||'smart'];
    return rows.sort(function(a,b){ return key(a)-key(b); });
  }
  /* باز کردن یک فروشگاه از بیرون (دستیار): همان دسته و محصول انتخاب می‌شود و صفحهٔ فهرست یا نقشه باز می‌شود */
  function openStoreFrom(cat, sid, title, to){
    if(state.cat!==cat){ var c = catById(cat); qEl.value = c ? c.name : ''; setCat(cat); }
    var p = prodByTitle(title);
    state.tab = 'results'; state.compare = false; state.info = false;
    if(p) state.product = p.id;
    state.selected = sid;
    if(to==='map'){ goView('map', {noFit:true}); setSheet('peek'); renderAll(); fitResults(); revealStore(sid); }
    else {
      goView('list'); renderAll();
      requestAnimationFrame(function(){ var el = cardsEl.querySelector('.card[data-sid="'+sid+'"]'); if(el) el.scrollIntoView({block:'start', behavior:reduced?'auto':'smooth'}); });
    }
  }
  /* محصولات یک دسته برای تربچت (بدون فیلترهای صفحهٔ فهرست)، ارزان‌ترین اول */
  function chatProducts(cat){
    return (PRODS[cat]||[]).map(function(p){ return {p:p, s:prodStats(p, cat, true)}; }).filter(function(x){ return x.s.n>0; })
      .sort(function(a,b){ return (a.s.min||Infinity)-(b.s.min||Infinity); })
      .map(function(x){ return {cat:cat, id:x.p.id, title:x.p.title, tagline:x.p.tagline||'', art:artHTML(x.p, x.s), specs:x.p.specs||[],
        min:x.s.min, max:x.s.max, n:x.s.n, live:x.s.live, near:x.s.near, colors:x.s.colors}; });
  }
  /* فروشگاهی که اسمش در متن آمده (دو کلمهٔ اول نام کافی است) */
  function findStore(text){
    var q = norm(text);
    return Object.keys(STORES).filter(function(sid){
      var w = STORES[sid].name.split(/\s+/).slice(0, 2).join(' '), n = norm(w);
      return n.length > 3 && q.indexOf(n) > -1;
    });
  }
  /* محصول‌هایی که اسم مدلشان در متن آمده (مثلاً «Aura 520») */
  function findProducts(text){
    var q = norm(text), out = [];
    Object.keys(PRODS).forEach(function(cat){
      (PRODS[cat]||[]).forEach(function(p){
        var m = norm(modelOf(p.title)), first = norm(modelOf(p.title).split(' ')[0]);
        if((m && q.indexOf(m)>-1) || (first.length>3 && /[a-z]/.test(first) && q.indexOf(first)>-1)) out.push({cat:cat, id:p.id});
      });
    });
    return out;
  }
  /* مقایسهٔ چند محصول برای کارت جمع‌وجور تربچت: تفاوت‌های کلیدی مشخصات */
  function chatCompare(cat, ids){
    var all = chatProducts(cat), items = ids.map(function(id){ return all.filter(function(x){return x.id===id})[0]; }).filter(Boolean);
    if(items.length<2) return null;
    var labels = [], diffs = [];
    items.forEach(function(x){ x.specs.forEach(function(r){ if(labels.indexOf(r[0])<0) labels.push(r[0]); }); });
    labels.forEach(function(l){
      var v = items.map(function(x){ var r = x.specs.filter(function(y){return y[0]===l})[0]; return r ? r[1] : '—'; });
      if(!allSame(v)) diffs.push([l].concat(v));
    });
    return {items:items, diffs:diffs};
  }
  function openChatCompare(cat, ids){
    var prods = ids.map(function(id){ return prodOf(cat, id); }).filter(Boolean); if(prods.length<2) return;
    $('#cmpDlgTitle').textContent = 'مقایسهٔ کامل '+fa(prods.length)+' محصول';
    $('#cmpDlgBody').innerHTML = fullCmpHTML(prods, cat);
    if(typeof cmpDlg.showModal==='function') cmpDlg.showModal(); else cmpDlg.setAttribute('open','');
    $('#cmpDlgBody').scrollTop = 0;
  }
  /* باز کردن یک محصول از تربچت در صفحهٔ فهرست (فروشگاه‌های همان محصول) */
  function openProductFrom(cat, pid){
    if(state.cat!==cat){ var c = catById(cat); qEl.value = c ? c.name : ''; setCat(cat); }
    state.tab = 'results'; state.compare = false; state.selected = null;
    goView('list'); selectProduct(pid);
  }
  NQ.AgentUI.init({
    findCat: findCat, catById: catById, norm: norm, esc: esc, fa: fa, fa1: fa1, stock: STOCK, icons: IC, toast: toast,
    offers: suggestOffers,
    products: chatProducts, findProducts: findProducts, compare: chatCompare, model: modelOf,
    areas: NQ.AREAS || [], area: areaQuery, showArea: showArea, storeInfo: storeInfo, findStore: findStore,
    storeDialog: openStoreDlg, storeOnMap: storeOnMap,
    openCompare: openChatCompare, openProduct: openProductFrom,
    priceRange: chatPriceRange, brands: chatBrands, recommend: recommend, etaMode: etaModeHTML, travelLabel: function(id){ return Travel.label(id); },
    offerCompare: offerCmpData, openOfferCompare: openOfferCompare,
    guide: storeGuide, callStore: function(sid){ callStore(sid); }, locate: function(){ locateMe(false); },
    inquiries: function(){ return inqs.slice(); }, inqLabel: function(st){ return IQ_ST[st]; }, inqBadge: inqBadge, goView: function(v){ goView(v); },
    /* برنامهٔ سر زدن (همان که در فهرست و نقشه است) برای پنل «سر زدن‌ها» */
    plan: {
      list: function(){
        var S = Plan.schedule(state.origin), bySid = {};
        S.rows.forEach(function(r){ bySid[r.st.sid] = r; });
        return Plan.stops.map(function(st){
          var r = bySid[st.sid] || {}, so = STORES[st.sid];
          return {sid: st.sid, name: so.name, art: storeArtHTML(st.sid), done: !!st.done, addr: so.addr, hours: so.hours,
            n: r.n || 0, arrive: r.arrive ? hm(r.arrive) : '', statusK: r.done ? 'done' : r.status || '', status: r.done ? 'سر زدید' : r.status ? statusText(r) : '',
            leg: r.km ? fa1(r.km)+' کیلومتر · <span class="eta">'+IC[r.mode]+'<span>'+dur(r.tm)+'</span></span>' : '',
            items: st.cats.map(function(c){ var x = (OFFERS[c]||[]).filter(function(y){return y[0]===st.sid})[0]; return {cat: c, label: (catById(c)||{}).name || '', title: x ? x[1] : '', price: x ? x[3] : 0, stock: x ? x[4] : ''}; })};
        });
      },
      summary: function(){
        var S = Plan.schedule(state.origin);
        return S.active ? fa(S.active)+' توقف · '+fa1(S.totalKm)+' کیلومتر · حدود '+dur(S.totalMin)+' · پایان ≈ '+hm(S.end) : '';
      },
      /* باز کردن برنامهٔ سر زدن در صفحهٔ فهرست یا نقشه؛ با sid همان فروشگاه انتخاب و اطلاعاتش باز می‌شود */
      open: function(sid, to){
        state.tab = 'plan'; state.planSel = null; state.planCmp = false;
        if(view!==to) goView(to, {noFit: true});
        if(to==='map') setSheet(sid ? 'full' : 'half');
        if(sid && planStop(sid)) planFocus(sid, true); else { renderAll(); fitPlan(); }
        if(!sid) listTop(false);
      },
      stock: STOCK,
      has: function(sid, cat){ return Plan.has(sid, cat); },
      toggle: function(sid, cat){ var v = Plan.toggle(sid, cat); renderAll(); return v; },
      remove: function(sid){ Plan.remove(sid); if(state.planSel===sid) state.planSel = null; renderAll(); },
      setDone: function(sid, v){ Plan.setDone(sid, v); renderAll(); },
      clear: function(){ Plan.clear(); state.planSel = null; renderAll(); }
    },
    eta: function(o){ return etaHTML(o.km, o.sid); },
    etaKm: function(km){ return etaHTML(km); },
    addToPlan: function(sid, cat){ if(!Plan.has(sid, cat)) Plan.toggle(sid, cat); },
    openStore: openStoreFrom,
    goPlan: function(){ state.tab = 'plan'; state.planSel = null; sheet = 'half'; goView('map'); setSheet('half'); renderAll(); fitPlan(); }
  });
  NQ.Account.init({
    esc: esc, fa: fa, toast: toast, icons: IC, LINKS: LINKS, Travel: Travel,
    cities: NQ.CITIES, city: function(){ return curCity; }, setCity: function(id){ if(setCity(id)){ fitCurrent(); return true; } return false; },
    onTravel: afterFilterChange,
    clearChats: function(){ NQ.AgentUI.clearAll(); }
  });

  /* ---------- boot ---------- */
  MapView.init($('#lmap'), {
    onPinClick: function (sid) { activate(sid, 'pin'); },
    onBackgroundClick: function () {
      if (state.tab === 'plan') { if (state.planSel) { state.planSel = null; renderAll(); } return; }
      if (state.selected) { state.selected = null; renderAll(); }
    },
    onMoveEnd: onMapMoved,
    /* موبایل: کاربر نقشه را جابه‌جا می‌کند ← فهرست پایین می‌رود تا فقط نوار خلاصه (نام فروشگاه انتخاب‌شده) بماند */
    onDragStart: function () { if (isMobile() && sheet !== 'peek') setSheet('peek'); },
    onOriginMove: function (ll) { state.origin = ll; you_hint.hidden = true; scheduleRender(); }
  });
  Plan.load();
  applyLayout();
  applyView(viewFromHash());
  fitResults();
})();
