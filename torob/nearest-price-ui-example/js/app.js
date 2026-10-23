/* نزدیک‌ترین قیمت — منطق برنامه (state، رندر فهرست و مقایسه، رویدادها)
   وابستگی‌ها: js/data.js و js/map.js (باید قبل از این فایل لود شوند) */
(function () {
  'use strict';
  var NQ = window.NQ, MapView = NQ.MapView;
  var STORES = NQ.STORES, CATS = NQ.CATS, OFFERS = NQ.OFFERS, COLORS = NQ.COLORS, STOCK = NQ.STOCK, Plan = NQ.Plan;

  document.documentElement.setAttribute('lang', 'fa');
  document.documentElement.setAttribute('dir', 'rtl');

  var $ = function(s){return document.querySelector(s)};
  var fa = function(n){return Number(n).toLocaleString('fa-IR')};
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
  function etaText(km){
    return km<1.2 ? fa(Math.max(1,Math.round(km*12)))+' دقیقه پیاده' : fa(Math.max(2,Math.round(km*3)))+' دقیقه با ماشین';
  }
  function ago(h){return h<1 ? 'چند دقیقه پیش' : h<24 ? fa(Math.round(h))+' ساعت پیش' : fa(Math.round(h/24))+' روز پیش'}
  function lt(l){return '<b class="lt '+l.toLowerCase()+'">'+l+'</b>'}

  /* ---------- state ---------- */
  var state = {cat: 'headphone', product: null, info: false, sort: 'price', onlyOk: false, compare: false, picks: {A: null, B: null}, selected: null,
               pinfo: {}, pcmp: {A: null, B: null},
               origin: {lat: NQ.ORIGIN.lat, lng: NQ.ORIGIN.lng}};

  state.tab = 'results'; state.planSel = null;
  var lastSched = null;
  var you_hint = $('#hint'), cardsEl = $('#cards'), prodsEl = $('#prods'), pcmpEl = $('#pcmp'), pickBarEl = $('#pickBar'), cmpEl = $('#cmp'), scrollEl = $('#scroll'), qEl = $('#q');

  function catById(id){return CATS.filter(function(c){return c.id===id})[0]||null}
  function mk(r){
    var st = STORES[r[0]];
    return {sid:r[0],title:r[1],color:r[2],price:r[3],stock:r[4],hrs:r[5],store:st,km:roadKm(state.origin,st)};
  }
  function offer(sid){
    var p = curProd();
    var r = (OFFERS[state.cat]||[]).filter(function(x){return x[0]===sid && (!p || x[1]===p.title)})[0];
    return r ? mk(r) : null;
  }
  /* بدون محصولِ انتخاب‌شده همهٔ پیشنهادهای دسته برمی‌گردد (برای جاگیری نقشه و مرحلهٔ انتخاب مدل) */
  function offerRows(){
    if(!state.cat) return [];
    var p = curProd();
    return OFFERS[state.cat].filter(function(r){return !p || r[1]===p.title}).map(mk);
  }

  /* ---------- محصولات (مدل‌ها) ---------- */
  var PRODS = NQ.PRODUCTS || {};
  function prodsOf(cat){return PRODS[cat]||[]}
  function prodById(id){return prodsOf(state.cat).filter(function(p){return p.id===id})[0]||null}
  function prodByTitle(t){return prodsOf(state.cat).filter(function(p){return p.title===t})[0]||null}
  function curProd(){return state.product ? prodById(state.product) : null}
  /* none: هنوز دسته‌ای نیست · pick: مدل را انتخاب کنید · stores: فهرست فروشگاه‌های یک مدل */
  function stage(){
    if(!state.cat) return 'none';
    if(!prodsOf(state.cat).length) return 'stores';
    return curProd() ? 'stores' : 'pick';
  }
  function shortOf(t){return String(t).replace(/^\S+\s+/,'')}

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
    if(state.onlyOk) rows = rows.filter(function(o){return o.stock==='in'});
    var m = meta();
    var key = {
      price:function(o){return o.price},
      near:function(o){return o.km},
      smart:function(o){return o.price/(m.min||1)+o.km*.06+(o.stock==='unsure'?.12:0)}
    }[state.sort];
    rows.sort(function(a,b){return ((a.stock==='out')-(b.stock==='out')) || (key(a)-key(b))});
    return rows;
  }
  function slotOf(sid){return state.picks.A===sid?'A':state.picks.B===sid?'B':null}

  /* ---------- نقشه ---------- */
  function fitPoints(P) { MapView.fit(P); }
  function fitResults() {
    var rows = offerRows();
    fitPoints([state.origin].concat(rows.map(function (o) { return o.store; })));
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
    $('#cmpToggle').setAttribute('aria-pressed',String(state.compare));
    $('#onlyOk').checked = state.onlyOk;
    var st = stage();
    $('#sort').hidden = st!=='stores';
    document.querySelector('#toolbar .opts').hidden = st!=='stores';
  }
  function renderSummary(rows){
    var el = $('#summary'), c = catById(state.cat);
    if(!c){el.textContent='نام یک محصول را بنویسید یا از گزینه‌های بالا انتخاب کنید.';return}
    if(stage()==='pick'){
      el.innerHTML = '<b>'+fa(prodsOf(state.cat).length)+' محصول</b> برای «'+c.name+'» پیدا شد · یکی را انتخاب کنید تا فروشگاه‌ها را ببینید'+(prodsOf(state.cat).length>1?'، یا با آیکون مقایسه دو محصول را کنار هم بگذارید.':'.');
      return;
    }
    var m = meta(), p = curProd();
    var n = offerRows().length;
    el.innerHTML = '<b>'+fa(n)+' فروشگاه</b> برای '+(p?p.title:c.name)+(m.min?' · قیمت از '+fa(Math.round(m.min/1000))+' تا '+fa(Math.round(m.max/1000))+' هزار تومان':'');
  }
  function cardHTML(o,m,i){
    var sel = state.selected===o.sid && !state.compare, slot = slotOf(o.sid);
    var tags = '';
    if(o.sid===m.best) tags += '<span class="tag best">ارزان‌ترین</span>';
    if(o.sid===m.near) tags += '<span class="tag near">نزدیک‌ترین</span>';
    var diff = (o.stock!=='out' && o.price>m.min) ? '<em>'+fa(Math.round((o.price-m.min)/1000))+' هزار بیشتر از ارزان‌ترین</em>' : '';
    var stale = o.hrs>=48 ? '<span class="stale">قیمت قدیمی</span>' : '';
    var cls = 'card '+o.stock+(sel?' sel':'')+(slot?' slot-'+slot.toLowerCase():'');
    var saved = Plan.has(o.sid,state.cat);
    var saveLbl = saved ? 'برداشتن از برنامهٔ سر زدن' : 'ذخیره در برنامهٔ سر زدن';
    var saveBtn = '<button type="button" class="save-btn" data-save="'+o.sid+'" aria-pressed="'+saved+'" aria-label="'+saveLbl+'" title="'+saveLbl+'">' +
      '<svg width="19" height="19" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"/></svg></button>';
    var h = '<li style="--i:'+Math.min(i||0,10)+'"><article class="'+cls+'" data-sid="'+o.sid+'">' +
      '<button type="button" class="card-main" data-sid="'+o.sid+'" aria-pressed="'+(sel||!!slot)+'">' +
        (state.compare ? '<span class="pickmark'+(slot?' '+slot.toLowerCase():'')+'">'+(slot||'')+'</span>' : '') +
        '<span class="c-body">' +
          '<span class="c-row"><span class="c-name">'+o.store.name+'</span>'+tags+'</span>' +
          '<span class="c-var"><i class="sw" style="background:'+COLORS[o.color]+'"></i>'+(curProd()?'':o.title+' · ')+o.color+'</span>' +
          '<span class="c-meta"><span class="stock '+o.stock+'">'+STOCK[o.stock]+'</span><span>'+ago(o.hrs)+'</span><span>'+fa1(o.km)+' کیلومتر · '+etaText(o.km)+'</span>'+stale+'</span>' +
        '</span>' +
        '<span class="c-price"><b>'+fa(o.price)+'</b><small>تومان</small>'+diff+'</span>' +
      '</button>' + saveBtn;
    if(sel){
      h += '<dl class="det"><dt>نشانی</dt><dd>'+o.store.addr+'</dd><dt>ساعت کار</dt><dd>'+o.store.hours+'</dd><dt>تلفن</dt><dd>'+o.store.phone+'</dd>' +
        (o.stock==='unsure' ? '<dd class="note">آخرین بروزرسانی موجودی '+ago(o.hrs)+' بوده است. پیش از رفتن تماس بگیرید.</dd>' : '') +
        (o.stock==='out' ? '<dd class="note">این فروشگاه فعلاً این محصول را ندارد.</dd>' : '') +
        '</dl>';
    }
    return h+'</article></li>';
  }
  function renderList(rows){
    if(stage()==='pick'){cardsEl.innerHTML='';return}
    if(!rows.length){
      var msg;
      if(!state.cat) msg = qEl.value.trim() ? '«'+esc(qEl.value.trim())+'» در داده‌های نمونه نیست. یکی از محصولات بالا را امتحان کنید.' : 'برای دیدن فروشگاه‌ها یک محصول جستجو کنید.';
      else msg = 'فروشگاهی با موجودی تأییدشده پیدا نشد. فیلتر را بردارید تا همهٔ فروشگاه‌ها را ببینید.';
      cardsEl.innerHTML = '<li class="empty">'+msg+'</li>';
      return;
    }
    var m = meta();
    cardsEl.innerHTML = rows.map(function(o,i){return cardHTML(o,m,i)}).join('');
  }
  function renderPins(rows) {
    if (stage() === 'pick') {   // پین خنثی: نام مدلی که هر فروشگاه دارد؛ کلیک = انتخاب همان مدل
      MapView.renderPins(offerRows().map(function (o) {
        var p = prodByTitle(o.title);
        return {sid: o.sid, lat: o.store.lat, lng: o.store.lng, cls: '', html: '<span class="pp">' + esc(shortOf(o.title)) + '</span>',
                label: o.store.name + '، ' + o.title, z: 0};
      }));
      return;
    }
    var m = meta();
    MapView.renderPins(rows.map(function (o) {
      var slot = slotOf(o.sid), sel = state.selected === o.sid && !state.compare;
      return {
        sid: o.sid, lat: o.store.lat, lng: o.store.lng,
        cls: o.stock + (o.sid === m.best ? ' best' : '') + (slot ? ' slot-' + slot.toLowerCase() : '') + (sel ? ' sel' : '') + (Plan.has(o.sid, state.cat) ? ' saved' : ''),
        html: '<span class="pp">' + (slot ? '<b class="pl">' + slot + '</b>' : '') + fa(Math.round(o.price / 1000)) + (o.stock === 'unsure' ? '<sup>؟</sup>' : '') + '</span>',
        label: o.store.name + '، ' + fa(o.price) + ' تومان، ' + STOCK[o.stock],
        z: sel ? 4000 : slot ? 3000 : o.sid === m.best ? 1000 : 0
      };
    }));
  }
  function renderRoutes() {
    var lines = [], o = state.origin;
    function add(P, Q, cls) { lines.push({from: P, to: Q, cls: cls, text: fa1(roadKm(P, Q)) + ' کیلومتر'}); }
    if (state.compare) {
      var A = state.picks.A && STORES[state.picks.A], B = state.picks.B && STORES[state.picks.B];
      if (A) add(o, A, 'a');
      if (B) add(o, B, 'b');
      if (A && B) add(A, B, 'ab');
    } else if (state.selected && STORES[state.selected]) {
      add(o, STORES[state.selected], 'sel');
    }
    MapView.renderRoutes(lines);
  }
  function slotHTML(L,o){
    var l = L.toLowerCase();
    if(!o) return '<div class="slot empty">'+lt(L)+'<span>فروشگاه '+L+' را از لیست یا نقشه انتخاب کنید</span></div>';
    return '<div class="slot '+l+'">' +
      '<div class="s-top">'+lt(L)+'<span class="s-name">'+o.store.name+'</span><button type="button" class="s-x" data-unpick="'+L+'" aria-label="حذف فروشگاه '+L+'">×</button></div>' +
      '<span class="c-var"><i class="sw" style="background:'+COLORS[o.color]+'"></i>'+o.title+' · '+o.color+'</span>' +
      '<span class="s-price"><b>'+fa(o.price)+'</b> تومان</span>' +
      '<span class="stock '+o.stock+'">'+STOCK[o.stock]+'</span>' +
      '<span class="s-dist">'+fa1(o.km)+' کیلومتر تا شما · '+etaText(o.km)+'</span></div>';
  }
  function tipsFor(A,B){
    var t = [], both = [['A',A],['B',B]];
    if(A.stock!=='out' && B.stock!=='out'){
      var d = Math.abs(A.price-B.price);
      if(d===0) t.push('قیمت دو فروشگاه برابر است.');
      else t.push(lt(A.price<B.price?'A':'B')+' '+fa(Math.round(d/1000))+' هزار تومان ارزان‌تر است.');
    }
    if(A.title!==B.title) t.push('مدل دو فروشگاه فرق دارد، پس قیمت‌ها را نمی‌شود یک‌به‌یک مقایسه کرد.');
    else if(A.color!==B.color) t.push('رنگ دو فروشگاه فرق دارد.');
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
      var ab = roadKm(A.store,B.store), firstA = A.km<=B.km;
      var f = firstA?'A':'B', s = firstA?'B':'A';
      var total = Math.min(A.km,B.km)+ab, other = Math.max(A.km,B.km)+ab, round = A.km+ab+B.km;
      h += '<dl class="facts">' +
        '<div><dt>فاصلهٔ دو فروشگاه از هم</dt><dd>'+fa1(ab)+' کیلومتر · '+etaText(ab)+'</dd></div>' +
        '<div><dt>مسیر پیشنهادی</dt><dd><span class="chain">شما <i>←</i> '+lt(f)+' <i>←</i> '+lt(s)+'</span> · '+fa1(total)+' کیلومتر</dd></div>' +
        '<div><dt>ترتیب برعکس</dt><dd>'+fa1(other)+' کیلومتر</dd></div>' +
        '<div><dt>رفت‌وبرگشت کامل</dt><dd>'+fa1(round)+' کیلومتر</dd></div>' +
        '</dl><ul class="tips">'+tipsFor(A,B).map(function(x){return '<li><span>'+x+'</span></li>'}).join('')+'</ul>';
    } else {
      h += '<p class="cmp-hint">'+(!A&&!B ? 'دو فروشگاه را انتخاب کنید تا قیمت، موجودی و مسیر را کنار هم ببینید.' : 'یک فروشگاه دیگر انتخاب کنید.')+'</p>';
    }
    cmpEl.innerHTML = h+'</section>';
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
  function planItemsHTML(st) {
    return st.cats.map(function (cid) {
      var c = catById(cid), r = (OFFERS[cid] || []).filter(function (x) { return x[0] === st.sid; })[0];
      if (!c || !r) return '';
      return '<li class="pc-item'+(r[4]==='out'?' out':'')+'"><span class="it-topic">'+c.name+'</span>' +
        '<span class="it-title"><i class="sw" style="background:'+COLORS[r[2]]+'"></i>'+r[1]+' · '+r[2]+'</span>' +
        '<b class="it-price">'+fa(r[3])+'</b><span class="stock '+r[4]+'" title="'+STOCK[r[4]]+'"></span>' +
        '<button type="button" class="it-x" data-act="rmcat" data-sid="'+st.sid+'" data-cat="'+cid+'" aria-label="برداشتن «'+c.name+'» از این فروشگاه">×</button></li>';
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
    var plan = state.tab === 'plan';
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
      var sid = r.st.sid, sel = state.planSel === sid;
      var canUp = i > 0 && S.rows[i - 1].done === r.done, canDn = i < S.rows.length - 1 && S.rows[i + 1].done === r.done;
      var cls = 'pcard' + (r.done ? ' done' : ' st-' + r.status) + (sel ? ' sel' : '');
      var leg = '', badge = '';
      if (!r.done) {
        leg = '<p class="pc-leg">از ' + prev + ': ' + fa1(r.km) + ' کیلومتر · ' + dur(r.tm) + ' · رسیدن حدود <b>' + hm(r.arrive) + '</b></p>';
        badge = '<span class="badge ' + r.status + '">' + statusText(r) + '</span>';
        prev = r.S.name;
      } else badge = '<span class="badge done">انجام شد</span>';
      return '<li style="--i:' + Math.min(i, 10) + '"><article class="' + cls + '" data-sid="' + sid + '">' +
        '<div class="pc-top"><span class="pn">' + (r.done ? '✓' : fa(r.n)) + '</span>' +
          '<div class="pc-info"><button type="button" class="pc-name" data-act="focus" data-sid="' + sid + '" aria-pressed="' + sel + '">' + r.S.name + '</button>' + badge + '</div>' +
          '<div class="pc-acts">' +
            '<button type="button" class="icon-btn sm" data-act="up" data-sid="' + sid + '" aria-label="بالاتر ببر (اولویت بیشتر)" title="بالاتر"' + (canUp ? '' : ' disabled') + '>' + ICON.up + '</button>' +
            '<button type="button" class="icon-btn sm" data-act="down" data-sid="' + sid + '" aria-label="پایین‌تر ببر" title="پایین‌تر"' + (canDn ? '' : ' disabled') + '>' + ICON.down + '</button>' +
            '<button type="button" class="icon-btn sm" data-act="rm" data-sid="' + sid + '" aria-label="حذف از برنامه" title="حذف">' + ICON.rm + '</button>' +
          '</div></div>' +
        leg +
        '<ul class="pc-items">' + planItemsHTML(r.st) + '</ul>' +
        '<div class="pc-foot"><span class="pc-addr">' + r.S.addr + ' · ' + r.S.hours + '</span>' +
          '<label class="check"><input type="checkbox" data-act="done" data-sid="' + sid + '"' + (r.done ? ' checked' : '') + '> سر زدم</label></div>' +
        '</article></li>';
    }).join('');
  }
  function renderPlanMap() {
    var S = lastSched, items = [], lines = [], pos = state.origin;
    S.rows.forEach(function (r) {
      var sel = state.planSel === r.st.sid;
      items.push({
        sid: r.st.sid, lat: r.S.lat, lng: r.S.lng,
        cls: 'plan ' + (r.done ? 'done' : 'st-' + r.status) + (sel ? ' sel' : ''),
        html: '<span class="pp"><b class="pn">' + (r.done ? '✓' : fa(r.n)) + '</b><span class="pn-name">' + r.S.name + '</span></span>',
        label: (r.done ? 'انجام شد: ' + r.S.name : fa(r.n) + '. ' + r.S.name + '، ' + statusText(r)),
        z: sel ? 4000 : r.done ? 0 : 1500
      });
      if (!r.done) { lines.push({from: pos, to: r.S, cls: 'plan', text: fa1(r.km) + ' کیلومتر'}); pos = r.S; }
    });
    MapView.renderPins(items);
    MapView.renderRoutes(lines);
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
    renderAll(); fitCurrent();
  }

  /* ---------- مرحلهٔ انتخاب مدل + نوار محصول ---------- */
  var CHEV_DOWN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
  var CHEV_GO = '<svg class="pr-go" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg>';
  function prodStats(p){
    var rows = OFFERS[state.cat].filter(function(r){return r[1]===p.title}).map(mk);
    var live = rows.filter(function(o){return o.stock!=='out'});
    var cnt = {}, colors = [];
    rows.forEach(function(o){cnt[o.color]=(cnt[o.color]||0)+1; if(colors.indexOf(o.color)<0) colors.push(o.color)});
    var main = colors.slice().sort(function(a,b){return cnt[b]-cnt[a]})[0];
    var prices = live.map(function(o){return o.price}), kms = live.map(function(o){return o.km});
    return {n:rows.length, live:live.length, colors:colors, main:main,
            min:prices.length?Math.min.apply(null,prices):0, max:prices.length?Math.max.apply(null,prices):0, near:kms.length?Math.min.apply(null,kms):0};
  }
  function artHTML(p,s){
    if(p.img) return '<img src="'+esc(p.img)+'" alt="" loading="lazy">';
    return NQ.art ? NQ.art(p.kind, COLORS[s.main]||'#8C9692') : '';
  }
  function swatches(cols){
    return '<span class="dots" aria-label="رنگ‌ها: '+cols.join('، ')+'">'+cols.map(function(c){return '<i class="sw" style="background:'+COLORS[c]+'" title="'+c+'"></i>'}).join('')+'</span>';
  }
  var lastProds = '', lastBar = '', lastPCmp = '';
  function pslotOf(id){return state.pcmp.A===id?'A':state.pcmp.B===id?'B':null}
  function cmpBtnHTML(id, slot){
    var lbl = slot ? 'برداشتن از مقایسه' : 'افزودن به مقایسه';
    return '<button type="button" class="cmp-ic'+(slot?' on-'+slot.toLowerCase():'')+'" data-pcmp="'+id+'" aria-pressed="'+!!slot+'" aria-label="'+lbl+'" title="'+lbl+'">' +
      (slot ? lt(slot) : ICON.cmp) + '</button>';
  }
  function renderProducts(){
    var html = '';
    if(stage()==='pick'){
      var list = prodsOf(state.cat).map(function(p){return {p:p,s:prodStats(p)}});
      var best = null, many = list.length>1;
      list.forEach(function(x){if(x.s.min && (!best || x.s.min<best.s.min)) best = x});
      html = list.map(function(x,i){
        var p = x.p, s = x.s, open = !!state.pinfo[p.id], slot = pslotOf(p.id);
        var price = s.min ? '<span class="pr-price"><small>از</small><b>'+fa(s.min)+'</b><small>تومان</small></span>' : '<span class="pr-price"><small>فعلاً ناموجود</small></span>';
        var range = s.min ? (s.max>s.min ? 'از '+fa(s.min)+' تا '+fa(s.max)+' تومان' : fa(s.min)+' تومان') : 'فعلاً در هیچ فروشگاهی موجود نیست';
        return '<li style="--i:'+i+'"><article class="prod'+(open?' open':'')+(slot?' slot-'+slot.toLowerCase():'')+'" data-id="'+p.id+'">' +
          '<button type="button" class="prod-main" data-prod="'+p.id+'" aria-label="دیدن فروشگاه‌های '+esc(p.title)+'">' +
            '<span class="pr-img">'+artHTML(p,s)+'</span>' +
            '<span class="pr-body">' +
              '<span class="pr-row"><span class="pr-name">'+esc(p.title)+'</span>'+(best===x && many ? '<span class="tag best">ارزان‌ترین</span>' : '')+'</span>' +
              '<span class="pr-desc">'+esc(p.tagline||'')+'</span>' +
              price +
              '<span class="pr-meta">'+swatches(s.colors)+'<span>'+fa(s.n)+' فروشگاه</span>'+(s.live ? '<span>نزدیک‌ترین '+fa1(s.near)+' کیلومتر</span>' : '')+'</span>' +
            '</span>' + CHEV_GO + '</button>' +
          '<div class="pr-foot">' +
            '<button type="button" class="pr-more" data-pinfo="'+p.id+'" aria-expanded="'+open+'" aria-controls="pd-'+p.id+'">'+ICON.info+'<span>مشاهدهٔ جزئیات</span>'+CHEV_DOWN+'</button>' +
            (many ? cmpBtnHTML(p.id, slot) : '') +
          '</div>' +
          '<div class="pr-det" id="pd-'+p.id+'"'+(open?'':' hidden')+'>' +
            '<p class="pr-range"><span>قیمت در فروشگاه‌ها</span><b>'+range+'</b></p>' +
            infoHTML(p,s) +
            '<button type="button" class="pr-go-btn" data-prod="'+p.id+'">دیدن '+fa(s.n)+' فروشگاه روی نقشه'+CHEV_GO+'</button>' +
          '</div>' +
        '</article></li>';
      }).join('');
    }
    if(html!==lastProds){prodsEl.innerHTML = html; lastProds = html}
  }
  /* ---------- مقایسهٔ دو محصول ---------- */
  function pslotHTML(L, p){
    if(!p) return '<div class="slot empty">'+lt(L)+'<span>محصول '+L+' را با آیکون مقایسه انتخاب کنید</span></div>';
    var s = prodStats(p);
    return '<div class="slot '+L.toLowerCase()+'">' +
      '<div class="s-top">'+lt(L)+'<span class="s-name" title="'+esc(p.title)+'">'+esc(shortOf(p.title))+'</span><button type="button" class="s-x" data-punpick="'+L+'" aria-label="حذف محصول '+L+' از مقایسه">×</button></div>' +
      '<div class="ps-row"><span class="ps-img">'+artHTML(p,s)+'</span>' +
        '<span class="ps-info">'+(s.min ? '<span class="s-price"><small>از</small> <b>'+fa(s.min)+'</b> تومان</span>' : '<span class="s-price">ناموجود</span>') +
        '<span class="s-dist">'+fa(s.n)+' فروشگاه</span></span></div>' +
      '<button type="button" class="ps-go" data-prod="'+p.id+'">دیدن فروشگاه‌ها</button></div>';
  }
  function renderPCmp(){
    var html = '';
    var A = state.pcmp.A && prodById(state.pcmp.A), B = state.pcmp.B && prodById(state.pcmp.B);
    if(stage()==='pick' && (A||B)){
      html = '<section class="cmp pcmp" aria-label="مقایسهٔ دو محصول"><div class="cmp-head"><h2>مقایسهٔ دو محصول</h2><button type="button" class="cmp-close" id="pcmpClose">بستن</button></div>' +
        '<div class="slots">'+pslotHTML('A',A)+pslotHTML('B',B)+'</div>';
      if(A && B){
        var sa = prodStats(A), sb = prodStats(B);
        var rows = [];
        function win(a,b,lowWins){ if(!a||!b||a===b) return ['','']; return (lowWins ? a<b : a>b) ? [' win',''] : ['',' win']; }
        var w = win(sa.min, sb.min, true);
        rows.push(['کمترین قیمت', sa.min?fa(sa.min)+' تومان':'ناموجود', sb.min?fa(sb.min)+' تومان':'ناموجود', w]);
        rows.push(['بیشترین قیمت', sa.max?fa(sa.max)+' تومان':'—', sb.max?fa(sb.max)+' تومان':'—', ['','']]);
        rows.push(['فروشگاه‌ها', fa(sa.n)+' ('+fa(sa.live)+' موجود)', fa(sb.n)+' ('+fa(sb.live)+' موجود)', win(sa.live, sb.live, false)]);
        rows.push(['نزدیک‌ترین', sa.live?fa1(sa.near)+' کیلومتر':'—', sb.live?fa1(sb.near)+' کیلومتر':'—', win(sa.live?sa.near:0, sb.live?sb.near:0, true)]);
        rows.push(['رنگ‌ها', swatches(sa.colors), swatches(sb.colors), ['',''], true]);
        var labels = [], ma = {}, mb = {};
        (A.specs||[]).forEach(function(r){ma[r[0]]=r[1]; if(labels.indexOf(r[0])<0) labels.push(r[0])});
        (B.specs||[]).forEach(function(r){mb[r[0]]=r[1]; if(labels.indexOf(r[0])<0) labels.push(r[0])});
        var diff = 0;
        labels.forEach(function(l){
          var a = ma[l]||'—', b = mb[l]||'—';
          if(a!==b) diff++;
          rows.push([l, esc(a), esc(b), ['',''], true, a!==b]);
        });
        html += '<div class="ptable" role="table" aria-label="مشخصات کنار هم">' +
          '<div class="pt-row pt-head" role="row"><span role="columnheader"></span><span role="columnheader">'+lt('A')+'</span><span role="columnheader">'+lt('B')+'</span></div>' +
          rows.map(function(r){
            return '<div class="pt-row'+(r[5]?' diff':'')+'" role="row"><span class="pt-l" role="rowheader">'+esc(r[0])+'</span>' +
              '<span role="cell" class="pt-v'+r[3][0]+'">'+r[1]+'</span><span role="cell" class="pt-v'+r[3][1]+'">'+r[2]+'</span></div>';
          }).join('') + '</div>';
        var tips = [];
        if(sa.min && sb.min){
          var d = Math.abs(sa.min-sb.min);
          tips.push(d ? lt(sa.min<sb.min?'A':'B')+' در ارزان‌ترین فروشگاه '+fa(Math.round(d/1000))+' هزار تومان ارزان‌تر است.' : 'کمترین قیمت دو محصول برابر است.');
        }
        if(sa.live && sb.live && Math.abs(sa.near-sb.near)>.3) tips.push('نزدیک‌ترین فروشگاهِ '+lt(sa.near<sb.near?'A':'B')+' به شما نزدیک‌تر است.');
        if(diff) tips.push(fa(diff)+' ویژگی با هم فرق دارد (ردیف‌های پررنگ).');
        if(tips.length) html += '<ul class="tips">'+tips.map(function(x){return '<li><span>'+x+'</span></li>'}).join('')+'</ul>';
      } else {
        html += '<p class="cmp-hint">'+(A||B ? 'محصول دیگری را با آیکون مقایسه انتخاب کنید تا مشخصات و قیمت را کنار هم ببینید.' : '')+'</p>';
      }
      html += '</section>';
    }
    if(html!==lastPCmp){pcmpEl.innerHTML = html; lastPCmp = html}
  }
  function togglePCmp(id){
    var c = state.pcmp;
    if(c.A===id) c.A=null;
    else if(c.B===id) c.B=null;
    else if(!c.A) c.A=id;
    else if(!c.B) c.B=id;
    else c.B=id;
    renderAll();
    if(c.A && c.B) scrollEl.scrollTo({top:0,behavior:reduced?'auto':'smooth'});
  }
  function togglePInfo(id){
    if(state.pinfo[id]) delete state.pinfo[id]; else state.pinfo[id] = true;
    renderProducts();
  }
  function infoHTML(p,s){
    var sp = (p.specs||[]).map(function(r){return '<div><dt>'+esc(r[0])+'</dt><dd>'+esc(r[1])+'</dd></div>'}).join('');
    var cols = s.colors.map(function(c){return '<li><i class="sw" style="background:'+COLORS[c]+'"></i>'+c+'</li>'}).join('');
    return (p.desc ? '<p class="sp-desc">'+esc(p.desc)+'</p>' : '') +
      (sp ? '<dl class="specs">'+sp+'</dl>' : '') +
      '<div class="sp-colors"><span>رنگ‌های موجود</span><ul>'+cols+'</ul></div>' +
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
    var html = '<section class="sp" tabindex="-1" aria-label="محصول انتخاب‌شده: '+esc(p.title)+'">' +
      '<div class="sp-main"><span class="sp-img">'+artHTML(p,s)+'</span>' +
        '<div class="sp-info"><span class="sp-name">'+esc(p.title)+'</span>' +
          '<span class="sp-sub">'+swatches(s.colors)+'<span>'+fa(s.n)+' فروشگاه</span>'+(s.min ? '<span>از <b>'+fa(s.min)+'</b> تومان</span>' : '')+'</span></div>' +
        (prodsOf(state.cat).length>1 ? '<button type="button" class="cmp-ic" id="spCmp" aria-label="مقایسه با محصول دیگر" title="مقایسه با محصول دیگر">'+ICON.cmp+'</button>' : '') +
        '<button type="button" class="sp-change" id="spChange">تغییر محصول</button></div>' +
      '<button type="button" class="sp-more" id="spMore" aria-expanded="'+open+'" aria-controls="spPanel"><span>مشاهدهٔ جزئیات</span>'+CHEV_DOWN+'</button>' +
      '<div class="sp-panel" id="spPanel"'+(open ? '' : ' hidden')+'>'+infoHTML(p,s)+'</div></section>';
    pickBarEl.hidden = false;
    if(html!==lastBar){pickBarEl.innerHTML = html; lastBar = html}
  }
  function bump(el){el.classList.add('enter'); clearTimeout(el._t); el._t = setTimeout(function(){el.classList.remove('enter')},900)}
  function selectProduct(id, sid){
    if(!prodById(id)) return;
    state.product = id; state.info = false; state.picks = {A:null,B:null}; state.selected = null;
    if(sid){ if(state.compare) state.picks.A = sid; else state.selected = sid; }
    bump(cardsEl);
    renderAll(); fitResults();
    scrollEl.scrollTo({top:0});
    if(sid){
      requestAnimationFrame(function(){
        var el = cardsEl.querySelector('.card[data-sid="'+sid+'"]');
        if(el) el.scrollIntoView({block:'nearest',behavior:reduced?'auto':'smooth'});
      });
    } else {
      var sp = pickBarEl.querySelector('.sp'); if(sp) sp.focus({preventScroll:true});
    }
  }
  function clearProduct(){
    state.product = null; state.info = false; state.picks = {A:null,B:null}; state.selected = null;
    bump(prodsEl);
    renderAll(); fitResults();
    scrollEl.scrollTo({top:0});
    var b = prodsEl.querySelector('.prod-main'); if(b) b.focus({preventScroll:true});
  }
  function compareFromBar(){
    var id = state.product; if(!id) return;
    if(state.pcmp.A!==id && state.pcmp.B!==id){ if(!state.pcmp.A) state.pcmp.A = id; else state.pcmp.B = id; }
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

  function renderAll() {
    var rows = visibleRows();
    renderTabs();
    renderChips(); renderControls(); renderSummary(rows); renderCmp(); renderList(rows); renderPCmp(); renderProducts(); renderPickBar();
    renderPlan();
    if (state.tab === 'plan') renderPlanMap(); else { renderPins(rows); renderRoutes(); }
    MapView.setOrigin(state.origin);
  }
  var raf = 0;
  function scheduleRender() { if (raf) return; raf = requestAnimationFrame(function () { raf = 0; renderAll(); }); }

  /* ---------- actions ---------- */
  var enterTimer = 0;
  function setCat(id){
    var changed = id!==state.cat;
    state.cat = id; state.tab = 'results'; state.planSel = null;
    if(changed){state.picks={A:null,B:null};state.selected=null;state.product=null;state.info=false;state.pinfo={};state.pcmp={A:null,B:null};var ps=prodsOf(id);if(ps.length===1) state.product=ps[0].id}
    if(changed){cardsEl.classList.add('enter');clearTimeout(enterTimer);enterTimer=setTimeout(function(){cardsEl.classList.remove('enter')},900)}
    if(changed) bump(prodsEl);
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
      scrollEl.scrollTo({top:0,behavior:reduced?'auto':'smooth'});
    }
  }
  function activate(sid,from){
    if(state.tab==='plan'){
      state.planSel = state.planSel===sid ? null : sid;
      renderAll();
      if(state.planSel) requestAnimationFrame(function(){
        var el = planList.querySelector('.pcard[data-sid="'+sid+'"]');
        if(el) el.scrollIntoView({block:'nearest',behavior:reduced?'auto':'smooth'});
      });
      return;
    }
    if(stage()==='pick'){ pickFromPin(sid); return; }
    if(state.compare) togglePick(sid);
    else {
      state.selected = state.selected===sid ? null : sid;
      renderAll();
      if(from==='pin' && state.selected){
        requestAnimationFrame(function(){
          var el = cardsEl.querySelector('.card[data-sid="'+sid+'"]');
          if(el) el.scrollIntoView({block:'nearest',behavior:reduced?'auto':'smooth'});
        });
      }
    }
  }

  /* ---------- events: list, search, toolbar ---------- */
  cardsEl.addEventListener('click',function(e){
    var sv = e.target.closest('.save-btn'); if(sv){toggleSave(sv.getAttribute('data-save'));return}
    var b = e.target.closest('.card-main'); if(b) activate(b.getAttribute('data-sid'),'list');
  });
  cmpEl.addEventListener('click',function(e){
    var x = e.target.closest('[data-unpick]');
    if(x){state.picks[x.getAttribute('data-unpick')]=null;renderAll();return}
    if(e.target.closest('#cmpClose')){state.compare=false;state.picks={A:null,B:null};renderAll()}
  });
  prodsEl.addEventListener('click',function(e){
    var t;
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
    if((t = e.target.closest('[data-prod]'))) selectProduct(t.getAttribute('data-prod'));
  });
  pcmpEl.addEventListener('click',function(e){
    var t;
    if((t = e.target.closest('[data-punpick]'))){ state.pcmp[t.getAttribute('data-punpick')] = null; renderAll(); return; }
    if(e.target.closest('#pcmpClose')){ state.pcmp = {A:null,B:null}; renderAll(); return; }
    if((t = e.target.closest('[data-prod]'))) selectProduct(t.getAttribute('data-prod'));
  });
  pickBarEl.addEventListener('click',function(e){
    if(e.target.closest('#spMore')){toggleInfo();return}
    if(e.target.closest('#spCmp')){compareFromBar();return}
    if(e.target.closest('#spChange')) clearProduct();
  });
  $('#chips').addEventListener('click',function(e){
    var b = e.target.closest('.chip'); if(!b) return;
    var c = catById(b.getAttribute('data-cat'));
    qEl.value = c.name; setCat(c.id);
  });
  qEl.addEventListener('input',function(){var c=findCat(qEl.value);setCat(c?c.id:null)});
  $('#searchForm').addEventListener('submit',function(e){e.preventDefault();qEl.blur()});
  $('#clearQ').addEventListener('click',function(){qEl.value='';setCat(null);qEl.focus()});
  $('#sort').addEventListener('click',function(e){
    var b = e.target.closest('button'); if(!b) return;
    state.sort = b.getAttribute('data-sort'); renderAll();
  });
  $('#onlyOk').addEventListener('change',function(e){state.onlyOk=e.target.checked;renderAll()});
  $('#cmpToggle').addEventListener('click',function(){
    state.compare = !state.compare;
    state.selected = null;
    if(!state.compare) state.picks={A:null,B:null};
    renderAll();
    if(state.compare) scrollEl.scrollTo({top:0,behavior:reduced?'auto':'smooth'});
  });

  /* ---------- events: برنامهٔ سر زدن ---------- */
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
    var b = e.target.closest('[data-act]'); if(!b || b.tagName==='INPUT') return;
    var act = b.getAttribute('data-act'), sid = b.getAttribute('data-sid');
    if(act==='up' || act==='down'){
      Plan.move(sid, act==='up' ? -1 : 1); renderAll();
      var again = planList.querySelector('[data-act="'+act+'"][data-sid="'+sid+'"]:not(:disabled)') || planList.querySelector('[data-act="focus"][data-sid="'+sid+'"]');
      if(again) again.focus();
    } else if(act==='rm'){
      Plan.remove(sid); if(state.planSel===sid) state.planSel=null; renderAll();
    } else if(act==='rmcat'){
      Plan.removeCat(sid, b.getAttribute('data-cat')); renderAll();
    } else if(act==='focus'){
      state.planSel = state.planSel===sid ? null : sid; renderAll();
      if(state.planSel) MapView.panTo(STORES[sid]);
    }
  });
  planList.addEventListener('change',function(e){
    var c = e.target.closest('[data-act="done"]'); if(!c) return;
    Plan.setDone(c.getAttribute('data-sid'), c.checked); renderAll();
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
  $('#zloc').addEventListener('click', function () {
    var btn = this; btn.disabled = true;
    MapView.locate(function (ll) {
      btn.disabled = false;
      var nearest = Math.min.apply(null, Object.keys(STORES).map(function (k) { return NQ.geo.distanceKm(ll, STORES[k]); }));
      if (nearest > 60) { toast(ZOOM_NOTE, 'warn'); return; }
      state.origin = ll; you_hint.hidden = true;
      renderAll(); fitCurrent();
    }, function (code) { btn.disabled = false; toast(GEO_ERR[code] || GEO_ERR.failed, 'warn'); });
  });

  /* ---------- theme (روشن / تاریک) ---------- */
  var root = document.documentElement;
  try { var saved = localStorage.getItem('nq-theme'); if (saved) root.setAttribute('data-theme', saved); } catch (e) {}
  $('#themeBtn').addEventListener('click', function () {
    var cur = root.getAttribute('data-theme') || (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    var next = cur === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('nq-theme', next); } catch (e) {}
  });

  /* ---------- boot ---------- */
  MapView.init($('#lmap'), {
    onPinClick: function (sid) { activate(sid, 'pin'); },
    onBackgroundClick: function () {
      if (state.tab === 'plan') { if (state.planSel) { state.planSel = null; renderAll(); } return; }
      if (state.selected) { state.selected = null; renderAll(); }
    },
    onOriginMove: function (ll) { state.origin = ll; you_hint.hidden = true; scheduleRender(); }
  });
  Plan.load();
  renderAll();
  fitResults();
})();
