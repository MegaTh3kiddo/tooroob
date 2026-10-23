/* ترب مپ — تربچت (دستیار خرید)
   دو بخش جدا:
   ۱) NQ.AgentBrain: «مغز» نمایشی. متن کاربر را می‌گیرد و پاسخ ساختاریافته برمی‌گرداند.
      در نسخهٔ واقعی فقط همین تابع respond با فراخوانی سرویس دستیار (LLM) جایگزین می‌شود؛
      قالب خروجی ثابت می‌ماند تا رابط کاربری دست نخورد.
   ۲) NQ.AgentUI: رابط گفتگو و «فهرست خرید». با api که app.js می‌دهد به بقیهٔ برنامه وصل است
      (پیشنهاد فروشگاه، باز کردن فروشگاه در فهرست/نقشه، افزودن به برنامهٔ سر زدن). */
(function (NQ) {
  'use strict';

  var faDigits = '۰۱۲۳۴۵۶۷۸۹';
  function toEn(s) { return String(s).replace(/[۰-۹]/g, function (d) { return faDigits.indexOf(d); }).replace(/[٫,،]/g, '.'); }

  /* چیزهایی که هنوز در داده‌های نمونه نیستند ولی دستیار باید بشناسد (برای کارهای «سر راه») */
  var KNOWN_MISSING = ['میوه', 'سبزی', 'نان', 'دارو', 'گوشت', 'مرغ', 'لبنیات', 'شیر', 'قهوه', 'گل', 'لوازم‌التحریر', 'کفش', 'لباس', 'سیم'];
  /* کلمه‌های اضافهٔ جمله (فقط کلمهٔ کامل، نه بخشی از یک کلمه) */
  var FILLER = /(^|\s)(می[‌ ]?خوام|می[‌ ]?خواهم|میخوام|بخرم|بگیرم|بخریم|لازم|دارم|برم|هم|یه|یک|یدونه|سر|راه|بعدش|بعد|اول|لطفا|لطفاً|برای|که)(?=\s|$)/g;

  /* ---------- ۱) مغز نمایشی ---------- */
  var MAX_ITEMS = 6;   // حداکثر فروشگاه یا محصول در یک پیام
  var GUIDE_RE = /چطوری\s*برم|چطور\s*برم|چجوری\s*برم|چطوری\s*برسم|آدرس|کجاست|کجا\s*هست|کجاس|پیدا\s*(ش|اش)?\s*نمی|نمی\s*‌?تونم\s*پیدا|گم\s*شدم|راهنمای\s*رسیدن/;
  var LOST_RE = /گم\s*شدم|پیدا\s*(ش|اش)?\s*نمی|نمی\s*‌?تونم\s*پیدا/;
  var WIZ_RE = /کمکم|کمک\s*کن|راهنماییم|نمی\s*‌?دونم\s*کدوم|کدومو\s*بخرم|کدوم\s*رو\s*بخرم|انتخاب\s*کنم|پیشنهاد\s*بده|چی\s*بخرم/;
  /* منطقه: «فروشگاه‌های این منطقه»، «اطراف من»، «منطقه‌ای که بیشترین ... دارد» */
  var AREA_RE = /منطقه|محله|اطراف|نزدیک\s*من|نزدیکم|دور\s*و\s*بر|حوالی|محدوده/;
  var HOT_RE = /بیشترین|تمرکز|شلوغ|پرتعداد|کجا\s*بیشتر/;
  var DIGITAL_RE = /دیجیتال|موبایل|کامپیوتر|لوازم\s*جانبی|الکترونیک/, FOOD_RE = /سوپر|هایپر|مواد\s*غذایی|خواربار|بقالی/;
  function areaIntent(t, api) {
    var n = api.norm(t), place = null;
    api.areas.forEach(function (a) { if (!place && a.words.some(function (w) { return n.indexOf(api.norm(w)) > -1; })) place = a.id; });
    var hot = HOT_RE.test(t);
    /* «اطراف من» یا «این منطقه» ← دور و بر کاربر؛ ولی «کجا بیشترین ...» بدون «من» ← کل شهر */
    var mine = /(^|\s)من(?=\s|$|[؟?.,،])|نزدیکم|اطرافم|دور\s*و\s*برم/.test(t);
    if (!place && (mine || (!hot && /نزدیک|اطراف|دور\s*و\s*بر|این\s*منطقه|این\s*محدوده|منطقه/.test(t)))) place = 'me';
    var km = toEn(t).match(/([\d.]+)\s*کیلومتر/);
    var c = api.findCat(t);
    return { cat: c ? c.id : null, kind: c ? null : DIGITAL_RE.test(t) ? 'digital' : FOOD_RE.test(t) ? 'food' : 'all', place: place, hotspot: hot, r: km ? parseFloat(km[1]) : 0 };
  }
  var ctx = { cats: [], maxPrice: 0, title: '' };
  function budgetOf(t) {
    var bm = toEn(t).match(/(زیر|تا|حداکثر|کمتر\s*از|کمتر)\s*([\d.]+)\s*(میلیون|هزار|تومان|تومن)?/);
    return bm ? Math.round(parseFloat(bm[2]) * (bm[3] === 'میلیون' ? 1e6 : bm[3] === 'هزار' ? 1e3 : 1)) : 0;
  }
  /* نکته‌های کلیدی مقایسه به زبان ساده: ارزان‌ترین، بیشترین فروشگاه و مهم‌ترین تفاوت‌های مشخصات (برای ۲ تا ۵ محصول) */
  function comparePoints(c, api) {
    var it = c.items, names = it.map(function (x) { return api.model(x.title); }), pts = [];
    var priced = it.filter(function (x) { return x.min; });
    var cheap = priced.slice().sort(function (a, b) { return a.min - b.min; })[0], dear = priced.slice().sort(function (a, b) { return b.min - a.min; })[0];
    if (cheap && dear && cheap !== dear) {
      var d = dear.min - cheap.min, amt = d >= 1e6 ? api.fa(Math.round(d / 1e5) / 10) + ' میلیون' : api.fa(Math.round(d / 1000)) + ' هزار';
      pts.push(api.model(cheap.title) + ' ارزون‌ترینه؛ حدود ' + amt + ' تومن کمتر از ' + api.model(dear.title) + '.');
    }
    var most = it.slice().sort(function (a, b) { return b.n - a.n; });
    if (most[0].n > most[1].n) pts.push(api.model(most[0].title) + ' تو فروشگاه‌های بیشتری هست (' + api.fa(most[0].n) + ' فروشگاه).');
    if (c.diffs.length) pts.push('فرق اصلی: ' + c.diffs.slice(0, 2).map(function (r) { return r[0]; }).join(' و ') + '.');
    var rec = cheap && c.diffs.length ? 'اگه قیمت برات مهم‌تره ' + api.model(cheap.title) + '؛ اگه ' + c.diffs[0][0] + ' مهم‌تره، جدول کامل رو ببین.' : '';
    var head = names.length === 2 ? 'مقایسهٔ ' + names[0] + ' و ' + names[1] + ':' : 'مقایسهٔ ' + api.fa(names.length) + ' مدل: ' + names.join('، ') + ':';
    return { head: head, points: pts, rec: rec };
  }
  var NUM_WORDS = { 'دو': 2, 'سه': 3, 'چهار': 4, 'پنج': 5 };
  /* چند محصول را مقایسه کنیم؟ «همه» ← ۵ · «سه تا» یا «۳ تا» ← ۳ · پیش‌فرض ۲ */
  function cmpCount(t) {
    if (/همه|همهٔ|تمام/.test(t)) return 5;
    var m = toEn(t).match(/([2-5])\s*(تا|مدل|محصول)/); if (m) return +m[1];
    var w = t.match(/(دو|سه|چهار|پنج)\s*(تا|مدل|محصول)/); if (w) return NUM_WORDS[w[1]];
    return 2;
  }
  NQ.AgentBrain = {
    reset: function () { ctx = { cats: [], maxPrice: 0, title: '' }; },
    /* خروجی: {text, groups:[{cat, label, note, offers}], products:[{cat, label, items}], compare:{cat,a,b,data,points}|null,
               missing:[label], route:bool, follow:[...]} */
    respond: function (text, api) {
      var t = String(text).trim(), out = { text: '', groups: [], products: [], stores: [], area: null, compare: null, wizard: null, guide: null, inq: false, missing: [], route: false, follow: [] };
      var budget = budgetOf(t);
      var sort = /ارزان|ارزون/.test(t) ? 'price' : /نزدیک/.test(t) ? 'near' : 'smart';
      var guarantee = /ضمانت/.test(t), openNow = /باز/.test(t) && /الان|الآن|همین/.test(t);
      var wantCmp = /مقایسه|بهتر(?!ین)|فرق|تفاوت|\sیا\s|\svs\s/i.test(' ' + t + ' ');
      var named = api.findProducts(t);

      /* ---- استعلام‌ها ---- */
      if (/استعلام/.test(t)) {
        var iq = api.inquiries();
        out.inq = true;
        out.text = iq.length ? 'آخرین استعلام‌هایی که برات گرفتم:' : 'هنوز استعلامی نگرفتی. تو اطلاعات هر فروشگاه «استعلام قیمت» رو بزن تا من از فروشنده بپرسم.';
        return out;
      }

      /* ---- راهنمای رسیدن / گم شدن ---- */
      if (GUIDE_RE.test(t)) {
        var gs = api.findStore(t)[0] || ctx.guideSid, lost = LOST_RE.test(t);
        if (!gs) {
          out.text = 'راهنمای رسیدن به کدوم فروشگاه؟';
          out.follow = api.plan.list().slice(0, 4).map(function (x) { return 'چطوری برم «' + x.name + '»؟'; });
          if (!out.follow.length) out.follow = ['چطوری برم «دیجی‌پلاس مرکز»؟', 'آدرس «گجت‌خانهٔ نارنج»'];
          return out;
        }
        ctx.guideSid = gs;
        out.guide = api.guide(gs, lost ? 2 : 1);
        out.text = lost ? 'نگران نباش؛ با این نشانه‌ها «' + out.guide.name + '» رو راحت پیدا می‌کنی:' : 'راهنمای رسیدن به «' + out.guide.name + '»:';
        return out;
      }

      /* ---- سؤال‌های کمکی: بودجه، برند، رفت‌وآمد، نزدیکی ← پیشنهاد نهایی ---- */
      if (WIZ_RE.test(t)) {
        var wc = (api.findCat(t) || {}).id || (named[0] || {}).cat || ctx.cats[0];
        if (!wc) { out.text = 'برای خرید چی کمک می‌خوای؟'; out.follow = ['کمکم کن هدفون بخرم', 'کمکم کن لپ‌تاپ انتخاب کنم', 'کمکم کن شارژر بخرم']; return out; }
        ctx.cats = [wc];
        ctx.wiz = { cat: wc };
        out.wizard = { cat: wc };
        out.text = 'باشه! چند تا سؤال کوتاه می‌پرسم تا بهترین فروشگاه‌ها رو برای ' + api.catById(wc).name + ' پیدا کنم.';
        return out;
      }

      /* ---- منطقه ---- */
      var namedArea = api.areas.some(function (ar) { return ar.words.some(function (w) { return api.norm(t).indexOf(api.norm(w)) > -1; }); });
      if (AREA_RE.test(t) || HOT_RE.test(t) || namedArea) {
        var q = areaIntent(t, api), a = api.area(q), what = q.cat ? api.catById(q.cat).name : q.kind === 'digital' ? 'لوازم دیجیتال' : q.kind === 'food' ? 'مواد غذایی' : 'فروشگاه';
        out.area = { q: q, data: a };
        var n = a.sids.length;
        if (q.hotspot) out.text = n ? 'بیشترین تمرکز ' + what + ' ' + a.label + 'ه: ' + api.fa(n) + ' فروشگاه تو شعاع ' + api.fa1(a.near.r) + ' کیلومتر (' + api.fa1(a.dist) + ' کیلومتر از تو).' : 'جایی با چند فروشگاه ' + what + ' کنار هم پیدا نکردم.';
        else out.text = n ? api.fa(n) + (q.cat ? ' فروشگاه که ' + what + ' دارن' : what === 'فروشگاه' ? ' فروشگاه' : ' فروشگاه ' + what) + (a.label ? ' ' + (q.place === 'me' ? 'اطرافت' : 'تو ' + a.label) : '') + ':' : 'تو ' + (a.label || 'این منطقه') + ' فروشگاهی پیدا نکردم.';
        out.follow = q.hotspot ? ['فروشگاه‌های اطراف من'] : ['کجا بیشترین ' + (q.cat ? what : 'فروشگاه لوازم دیجیتال') + ' هست؟'];
        if (q.cat) ctx.cats = [q.cat];
        return out;
      }

      /* ---- نام یک فروشگاه: کارت فروشنده ---- */
      var stores = api.findStore(t);
      if (stores.length && !named.length && !api.findCat(t)) {
        out.stores = stores.slice(0, MAX_ITEMS).map(api.storeInfo);
        out.text = stores.length > 1 ? 'این فروشگاه‌ها رو پیدا کردم:' : 'اطلاعات ' + out.stores[0].name + ':';
        return out;
      }

      /* ---- مقایسه: محصولات نام‌برده (تا ۵)، یا چند محصول اول یک دسته ---- */
      if (wantCmp) {
        var cc = null, ids = null, same = named.filter(function (x) { return named.length && x.cat === named[0].cat; });
        if (same.length >= 2) { cc = same[0].cat; ids = same.slice(0, 5).map(function (x) { return x.id; }); }
        else {
          cc = named.length ? named[0].cat : (api.findCat(t) || {}).id || ctx.cats[0];
          var list = cc ? api.products(cc) : [];
          if (list.length >= 2) {
            var first = named.length ? named[0].id : null;
            ids = (first ? [first] : []).concat(list.map(function (x) { return x.id; }).filter(function (id) { return id !== first; })).slice(0, cmpCount(t));
          }
        }
        var data = ids && api.compare(cc, ids);
        if (data) {
          var cp = comparePoints(data, api);
          out.compare = { cat: cc, ids: ids, data: data };
          out.text = cp.head + '\n' + cp.points.join('\n') + (cp.rec ? '\n' + cp.rec : '');
          out.follow = data.items.slice(0, 3).map(function (x) { return 'فروشگاه‌های ' + api.model(x.title); });
          ctx.cats = [cc];
          return out;
        }
      }

      /* ---- یک محصول مشخص: فروشگاه‌های همان محصول ---- */
      if (named.length === 1) {
        var np = api.products(named[0].cat).filter(function (x) { return x.id === named[0].id; })[0];
        if (np) {
          var offs = api.offers(np.cat, { sort: sort, guarantee: guarantee, openNow: openNow, title: np.title });
          ctx.cats = [np.cat]; ctx.title = np.title; ctx.maxPrice = budget;
          if (!offs.length) { out.text = api.model(np.title) + ' الان جایی موجود نیست.'; return out; }
          out.groups.push({ cat: np.cat, label: api.model(np.title), note: '', offers: offs.slice(0, MAX_ITEMS) });
          out.text = 'فروشگاه‌های ' + api.model(np.title) + ':';
          out.follow = ['ارزون‌ترها', 'نزدیک‌ترین', 'فقط با ضمانت ترب'];
          return out;
        }
      }

      /* ---- تکه‌تکه کردن به کارهای جدا: «میوه بخرم و سر راه شارژر» ---- */
      var parts = t.split(/\s*[،,؛;]\s*|\s+و\s+|\s+سر راه\s+|\s+بعدش\s+|\s+همچنین\s+/).filter(Boolean), cats = [];
      parts.forEach(function (p) {
        var c = api.findCat(p);
        if (c) { if (cats.indexOf(c.id) < 0) cats.push(c.id); return; }
        var miss = KNOWN_MISSING.filter(function (w) { return api.norm(p).indexOf(api.norm(w)) > -1; })[0];
        if (!miss) {   // اسم کالا را از جمله در می‌آوریم (حدسی)
          var guess = p.replace(FILLER, ' ').replace(FILLER, ' ').replace(/\s+/g, ' ').trim();
          if (guess && guess.length > 1 && guess.split(' ').length <= 3 && !/[؟?]/.test(p) && !/ارزان|ارزون|نزدیک|ضمانت|باز|مقایسه|بهتر/.test(p)) miss = guess;
        }
        if (miss && out.missing.indexOf(miss) < 0) out.missing.push(miss);
      });

      var follow = !cats.length && !out.missing.length && ctx.cats.length && (sort !== 'smart' || guarantee || openNow || budget);
      if (follow) cats = ctx.cats.slice();
      else ctx.title = '';
      if (cats.length) ctx.cats = cats;
      /* بودجه فقط برای همین درخواست (و پرسش‌های پیگیری روی همان) می‌ماند */
      if (budget) ctx.maxPrice = budget; else if (!follow) ctx.maxPrice = 0;

      if (!cats.length && !out.missing.length) {
        out.unknown = true;
        out.text = 'متوجه نشدم. اسم کالا رو بنویس، مثلاً «هدفون زیر ۲ میلیون».';
        out.follow = ['هدفون زیر ۲ میلیون', 'کیبورد مکانیکی', 'برنج با کالابرگ'];
        return out;
      }

      /* یک دسته با چند مدل و بدون پرسش پیگیری: اول خود محصول‌ها؛ فروشگاه‌ها با یک کلیک */
      if (cats.length === 1 && !out.missing.length && !follow) {
        var prods = api.products(cats[0]).filter(function (x) { return !ctx.maxPrice || (x.min && x.min <= ctx.maxPrice); });
        if (prods.length > 1) {
          out.products.push({ cat: cats[0], label: api.catById(cats[0]).name, items: prods.slice(0, MAX_ITEMS) });
          out.text = 'اینا مدل‌های ' + api.catById(cats[0]).name + (ctx.maxPrice ? ' تا ' + api.fa(ctx.maxPrice) + ' تومن' : '') + 'ن؛ هر کدوم رو بخوای فروشگاه‌هاشو نشون می‌دم.';
          out.follow = ['کمکم کن انتخاب کنم', 'مقایسهٔ ' + api.model(prods[0].title) + ' و ' + api.model(prods[1].title), 'فروشگاه‌های ' + api.model(prods[0].title)];
          return out;
        }
      }

      cats.forEach(function (id) {
        var c = api.catById(id), all = api.offers(id, { sort: sort, guarantee: guarantee, openNow: openNow, title: follow ? ctx.title : '' });
        var fit = ctx.maxPrice ? all.filter(function (o) { return o.price <= ctx.maxPrice; }) : all, note = '';
        if (ctx.maxPrice && !fit.length) { note = 'زیر این قیمت نبود؛ ارزون‌ترین‌ها:'; fit = api.offers(id, { sort: 'price' }); }
        if (!fit.length) { out.missing.push(c.name); return; }
        out.groups.push({ cat: id, label: follow && ctx.title ? api.model(ctx.title) : c.name, note: note, offers: fit.slice(0, MAX_ITEMS) });
      });

      var how = sort === 'price' ? 'ارزون‌ترین‌ها' : sort === 'near' ? 'نزدیک‌ترین‌ها' : 'بهترین‌ها';
      var lines = [];
      if (out.groups.length) lines.push(follow ? how + (guarantee ? ' با ضمانت ترب' : '') + (openNow ? ' که الان بازن' : '') + ':' :
        'اینا برای ' + out.groups.map(function (g) { return g.label; }).join(' و ') + (ctx.maxPrice ? ' تا ' + api.fa(ctx.maxPrice) + ' تومن' : '') + ':');
      if (out.missing.length) lines.push(out.missing.join(' و ') + ' فعلاً تو ترب‌مپ نیست؛ گذاشتمش تو سر زدن‌ها.');
      var nItems = out.groups.length + out.missing.length;
      if (nItems > 1) { out.route = true; lines.push('چند تا خرید داری؛ می‌تونم مسیرشو بچینم.'); }
      out.text = lines.join('\n');
      out.follow = out.groups.length ? ['ارزون‌ترها', 'نزدیک‌ترین', 'فقط با ضمانت ترب'] : ['هدفون بی‌سیم', 'شارژر ۶۵ وات'];
      /* یک کالای بیرون از دادهٔ نمونه ← دستیار بک‌اند روی کاتالوگ واقعی (اگر در دسترس نبود همین پاسخ می‌ماند) */
      if (!out.groups.length && out.missing.length === 1 && !out.route) out.unknown = true;
      return out;
    }
  };

  /* حالت گفتگو جداگانه برای هر گفتگو ذخیره می‌شود */
  NQ.AgentBrain.state = function () { return ctx; };
  NQ.AgentBrain.load = function (c) { ctx = c && c.cats ? JSON.parse(JSON.stringify(c)) : { cats: [], maxPrice: 0, title: '' }; };

  /* ---------- ۲) رابط کاربری ---------- */
  var api, $ = function (s) { return document.querySelector(s); };
  var agentEl, logEl, inputEl, errands = [], seq = 0, busy = false;
  var CHAT_KEY = 'nq-chats-v1', MAX_CHATS = 40, chats = [], curId = null;
  var LOGO = '<img src="img/torobchat.png" alt="" width="30" height="30">';
  var SUGGEST = ['هدفون بی‌سیم زیر ۲ میلیون', 'میوه بخرم، سر راه یه شارژر هم بگیرم', 'کیبورد مکانیکی و ماوس'];

  function esc(s) { return api.esc(s); }
  function scrollEnd() { requestAnimationFrame(function () { logEl.scrollTop = logEl.scrollHeight; }); }
  function chipsHTML(list) {
    return list.length ? '<div class="ag-chips">' + list.map(function (q) { return '<button type="button" class="ag-chip" data-ag-ask="' + esc(q) + '">' + esc(q) + '</button>'; }).join('') + '</div>' : '';
  }
  function syncEmpty() { agentEl.classList.toggle('is-empty', !logEl.children.length); }
  function bubble(who, html) {
    var el = document.createElement('div');
    el.className = 'ag-msg ' + who;
    el.innerHTML = (who.indexOf('bot') === 0 ? '<span class="ag-av" aria-hidden="true">' + LOGO + '</span>' : '') + '<div class="ag-b">' + html + '</div>';
    logEl.appendChild(el); syncEmpty(); scrollEnd();
    return el;
  }
  function offerCard(o, cat, opt) {
    opt = opt || {};
    var picked = api.plan.has(o.sid, cat);
    return '<article class="ag-card' + (picked ? ' picked' : '') + '">' +
      '<div class="ag-c-top"><span class="ag-c-art" aria-hidden="true">' + api.storeInfo(o.sid).art + '</span><b class="ag-c-name">' + esc(o.store.name) + '</b><span class="stock ' + o.stock + '">' + api.stock[o.stock] + '</span></div>' +
      '<p class="ag-c-prod">' + esc(o.title) + '</p>' +
      '<p class="ag-c-price"><b>' + api.fa(o.price) + '</b> تومان</p>' +
      '<p class="ag-c-meta"><span>' + api.fa1(o.km) + ' کیلومتر</span>' + (opt.mode ? api.etaMode(o.km, opt.mode) : api.eta(o)) + '</p>' +
      (opt.cmp ? '<label class="ag-csel"><input type="checkbox" data-csel="' + o.sid + '|' + cat + '|' + esc(o.title) + '"><span>مقایسه</span></label>' : '') +
      '<div class="ag-c-acts">' +
        '<button type="button" class="ag-pick" data-ag-pick="' + o.sid + '" data-cat="' + cat + '" data-title="' + esc(o.title) + '" data-price="' + o.price + '" data-store="' + esc(o.store.name) + '" aria-pressed="' + picked + '">' + (picked ? api.icons.check + 'فهرست' : 'انتخاب') + '</button>' +
        '<button type="button" class="ag-go" data-ag-store="' + o.sid + '" data-cat="' + cat + '" data-title="' + esc(o.title) + '">جزئیات</button>' +
        '<button type="button" class="ag-go" data-ag-open="map" data-sid="' + o.sid + '" data-cat="' + cat + '" data-title="' + esc(o.title) + '" aria-label="روی نقشه" title="روی نقشه">' + api.icons.map + '</button>' +
      '</div></article>';
  }
  /* کارت محصول: تصویر، نام، بازهٔ قیمت و تعداد فروشگاه؛ «فروشگاه‌ها» همین‌جا در گفتگو جواب می‌گیرد */
  function productCard(x) {
    var m = api.model(x.title);
    return '<article class="ag-prod">' +
      '<span class="ag-p-img">' + x.art + '</span>' +
      '<div class="ag-p-b"><b class="ag-p-name" title="' + esc(x.title) + '">' + esc(x.title) + '</b>' + (x.tagline ? '<small>' + esc(x.tagline) + '</small>' : '') + '</div>' +
      '<p class="ag-c-price">' + (x.min ? '<small>از</small> <b>' + api.fa(x.min) + '</b> تومان' : 'فعلاً ناموجود') + '</p>' +
      '<p class="ag-c-meta"><span>' + api.fa(x.n) + ' فروشگاه</span>' + (x.live ? '<span>نزدیک‌ترین ' + api.fa1(x.near) + ' کیلومتر</span>' : '') + '</p>' +
      '<div class="ag-c-acts">' +
        '<button type="button" class="ag-pick" data-ag-ask="فروشگاه‌های ' + esc(m) + '">فروشگاه‌ها</button>' +
        '<button type="button" class="ag-go" data-specs="' + x.id + '" data-sc="' + x.cat + '" aria-haspopup="dialog">جزئیات</button>' +
      '</div></article>';
  }
  /* کارت فروشنده: عکس، نام، نوع، امتیاز، نشان‌ها، باز/بسته، فاصله و نشانی؛ «جزئیات» در پنجره */
  function sellerCard(x) {
    var badges = (x.rating ? '<span class="ag-st-rate">★ ' + api.fa1(x.rating) + ' <small>(' + api.fa(x.years) + ' سال در ترب)</small></span>' : '') +
      (x.torobpay ? '<span class="ag-badge tp">ترب‌پی</span>' : x.guarantee ? '<span class="ag-badge gr">ضمانت ترب</span>' : '') +
      (x.fast ? '<span class="ag-badge fs">ارسال فوری</span>' : '');
    return '<article class="ag-store">' +
      '<div class="ag-st-top"><span class="ag-st-img" aria-hidden="true">' + x.art + '</span><div class="ag-st-h"><b class="ag-c-name" title="' + esc(x.name) + '">' + esc(x.name) + '</b><small>' + esc(x.kind) + '</small></div></div>' +
      (badges ? '<div class="ag-st-badges">' + badges + '</div>' : '') +
      '<p class="ag-c-meta"><span class="ostat ' + x.statusK + '">' + esc(x.status) + '</span><span>' + api.fa1(x.km) + ' کیلومتر</span>' + x.eta + '</p>' +
      '<p class="ag-st-addr" title="' + esc(x.addr) + '">' + esc(x.addr) + '</p>' +
      '<div class="ag-c-acts"><button type="button" class="ag-pick" data-ag-store="' + x.sid + '">جزئیات</button>' +
        '<button type="button" class="ag-go" data-ag-smap="' + x.sid + '" aria-label="روی نقشه" title="روی نقشه">' + api.icons.map + '</button></div>' +
    '</article>';
  }
  /* پیش‌نمایش نقشهٔ منطقه (SVG ساده): دایرهٔ منطقه، فروشگاه‌ها و «شما»؛ با کلیک، صفحهٔ نقشه باز می‌شود */
  function areaMap(a) {
    var W = 320, H = 150, P = 18, pts = a.stores.map(function (x) { return x; }), all = pts.slice();
    if (a.near) {
      var dLat = a.near.r / 111, dLng = a.near.r / (111 * Math.cos(a.near.lat * Math.PI / 180));
      all.push({ lat: a.near.lat + dLat, lng: a.near.lng }, { lat: a.near.lat - dLat, lng: a.near.lng }, { lat: a.near.lat, lng: a.near.lng + dLng }, { lat: a.near.lat, lng: a.near.lng - dLng });
    }
    all.push(a.origin);
    var kx = Math.cos(35.7 * Math.PI / 180);
    var minX = Math.min.apply(null, all.map(function (p) { return p.lng * kx; })), maxX = Math.max.apply(null, all.map(function (p) { return p.lng * kx; }));
    var minY = Math.min.apply(null, all.map(function (p) { return p.lat; })), maxY = Math.max.apply(null, all.map(function (p) { return p.lat; }));
    var sc = Math.min((W - 2 * P) / ((maxX - minX) || 1e-3), (H - 2 * P) / ((maxY - minY) || 1e-3));
    var ox = (W - (maxX - minX) * sc) / 2, oy = (H - (maxY - minY) * sc) / 2;
    function X(p) { return (ox + (p.lng * kx - minX) * sc).toFixed(1); }
    function Y(p) { return (oy + (maxY - p.lat) * sc).toFixed(1); }
    var g = '';
    for (var i = 1; i < 6; i++) g += '<path d="M0 ' + (i * H / 6) + 'H' + W + 'M' + (i * W / 6) + ' 0V' + H + '" class="am-grid"/>';
    g += '<path d="M0 ' + (H * .62) + 'C' + (W * .3) + ' ' + (H * .5) + ' ' + (W * .6) + ' ' + (H * .78) + ' ' + W + ' ' + (H * .6) + '" class="am-road"/><path d="M' + (W * .42) + ' 0C' + (W * .46) + ' ' + (H * .4) + ' ' + (W * .38) + ' ' + (H * .7) + ' ' + (W * .44) + ' ' + H + '" class="am-road"/>';
    if (a.near) g += '<circle cx="' + X(a.near) + '" cy="' + Y(a.near) + '" r="' + (a.near.r * sc / 111).toFixed(1) + '" class="am-area"/>';
    pts.forEach(function (x) { g += '<circle cx="' + X(x) + '" cy="' + Y(x) + '" r="5" class="am-store"/>'; });
    g += '<circle cx="' + X(a.origin) + '" cy="' + Y(a.origin) + '" r="5.5" class="am-you"/>';
    return '<svg class="ag-amap" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid slice" aria-hidden="true">' + g + '</svg>';
  }
  function areaCard(r) {
    var a = r.area.data, q = esc(JSON.stringify(r.area.q));
    return '<article class="ag-area">' +
      '<button type="button" class="ag-amap-btn" data-ag-area="map" data-q="' + q + '" aria-label="نمایش روی نقشه">' + areaMap(a) +
        '<span class="ag-amap-tag">' + api.icons.map + 'روی نقشه</span></button>' +
      '<div class="ag-area-b"><b>' + esc(a.label || 'همهٔ فروشگاه‌ها') + '</b><small>' + api.fa(a.sids.length) + ' فروشگاه' + (a.near ? ' · شعاع ' + api.fa1(a.near.r) + ' کیلومتر' : '') + (a.dist ? ' · ' + api.fa1(a.dist) + ' کیلومتر از تو' : '') + '</small></div>' +
      '<div class="ag-c-acts"><button type="button" class="ag-pick" data-ag-area="map" data-q="' + q + '">' + api.icons.map + 'روی نقشه</button>' +
        '<button type="button" class="ag-go" data-ag-area="list" data-q="' + q + '">در فهرست</button></div>' +
    '</article>';
  }
  /* مقایسهٔ جمع‌وجور (۲ تا ۵ محصول): ستون هر محصول + مهم‌ترین تفاوت‌ها؛ با کلیک، مقایسهٔ کامل در پاپ‌آپ */
  function compareCard(c) {
    var it = c.data.items, n = it.length, rows = c.data.diffs.slice(0, 3), ids = c.ids || it.map(function (x) { return x.id; });
    var priced = it.filter(function (x) { return x.min; }), cheapId = priced.length > 1 ? priced.slice().sort(function (a, b) { return a.min - b.min; })[0].id : '';
    var heads = it.map(function (x, i) {
      return '<div class="ag-cmp-p' + (x.id === cheapId ? ' cheap' : '') + '"><span class="ag-cmp-img">' + x.art + '<b class="nb nb-' + (i + 1) + '">' + api.fa(i + 1) + '</b></span><b>' + esc(api.model(x.title)) + '</b>' +
        '<small>' + (x.min ? 'از ' + api.fa(x.min) + ' تومان' : 'ناموجود') + '</small></div>';
    }).join(n === 2 ? '<span class="ag-vs">در برابر</span>' : '');
    return '<article class="ag-cmp n' + n + '" role="button" tabindex="0" data-ag-cmp="' + c.cat + '|' + ids.join(',') + '" aria-label="مقایسهٔ کامل ' + esc(it.map(function (x) { return api.model(x.title); }).join('، ')) + '">' +
      '<div class="ag-cmp-scroll"><div class="ag-cmp-in" style="--n:' + n + '">' +
        '<div class="ag-cmp-heads">' + heads + '</div>' +
        (rows.length ? '<ul class="ag-cmp-rows">' + rows.map(function (r) {
          return '<li><span class="ag-cr-l">' + esc(r[0]) + '</span><span class="ag-cr-vs">' + r.slice(1).map(function (v) { return '<span class="ag-cr-v">' + esc(v) + '</span>'; }).join('') + '</span></li>';
        }).join('') + '</ul>' : '') +
      '</div></div>' +
      '<span class="ag-cmp-more">' + api.icons.expand + 'مقایسهٔ کامل' + (c.data.diffs.length > 3 ? ' · ' + api.fa(c.data.diffs.length) + ' تفاوت' : '') + '</span>' +
    '</article>';
  }
  /* ================= سؤال‌های کمکی (ویجت‌ها) و پیشنهاد نهایی =================
     ترتیب: بودجه ← برند (اگر بیش از یک برند باشد) ← رفت‌وآمد ← نزدیکی ← پیشنهاد نهایی (با فیلتر قابل تغییر و مقایسه) */
  var WZ_STEPS = ['budget', 'brand', 'travel', 'near'];
  /* مبلغ کوتاه: ۱٫۳۵ میلیون، ۱۲٫۵ میلیون، ۸۵۰ هزار */
  function money(v) { return v >= 1e7 ? api.fa(Math.round(v / 1e5) / 10) + ' میلیون' : v >= 1e6 ? api.fa(Math.round(v / 1e4) / 100) + ' میلیون' : api.fa(Math.round(v / 1000)) + ' هزار'; }
  function wzSummary(step, w) {
    if (step === 'budget') { var b = w.budget; return !b || (!b.min && !b.max) ? 'بودجه مهم نیست' : b.min && b.max ? 'از ' + money(b.min) + ' تا ' + money(b.max) + ' تومن' : b.max ? 'تا ' + money(b.max) + ' تومن' : 'بیشتر از ' + money(b.min) + ' تومن'; }
    if (step === 'brand') return w.brands && w.brands.length ? 'برند: ' + w.brands.join('، ') : 'برند فرقی نمی‌کنه';
    if (step === 'travel') return 'با ' + api.travelLabel(w.mode || 'auto') + (w.maxMin ? '، حداکثر ' + api.fa(w.maxMin) + ' دقیقه' : '، زمانش مهم نیست');
    return w.nearKm ? 'تا ' + api.fa(w.nearKm) + ' کیلومتر از من' : 'نزدیکی مهم نیست';
  }
  function optBtn(attr, val, on, html) { return '<button type="button" class="wz-opt" ' + attr + '="' + val + '" aria-pressed="' + !!on + '">' + html + '</button>'; }
  function wzFoot(edit) { return '<div class="wz-foot"><button type="button" class="wz-ok" data-wz-ok>' + (edit ? 'اعمال' : 'تأیید') + '</button></div>'; }
  /* حد قیمت: دو دستگیره + میان‌بُرهای آماده + «مهم نیست» */
  function wzBudget(w, edit) {
    var r = api.priceRange(w.cat), b = w.budget || {}, lo = b.min || r.lo, hi = b.max || r.hi, a = r.lo + (r.hi - r.lo) / 3, z = r.lo + (r.hi - r.lo) * 2 / 3;
    a = Math.round(a / r.step) * r.step; z = Math.round(z / r.step) * r.step;
    return '<div class="wz" data-wz="budget" data-lo="' + r.lo + '" data-hi="' + r.hi + '">' +
      '<p class="wz-q">بودجه‌ت چقدره؟</p>' +
      '<div class="wz-opts">' + optBtn('data-wz-preset', r.lo + ',' + a, false, 'تا ' + money(a)) + optBtn('data-wz-preset', a + ',' + z, false, money(a) + ' تا ' + money(z)) +
        optBtn('data-wz-preset', z + ',' + r.hi, false, 'بیشتر از ' + money(z)) + optBtn('data-wz-preset', 'any', !w.budget && edit, 'مهم نیست') + '</div>' +
      '<div class="rng wz-rng" style="--lo:' + ((lo - r.lo) / (r.hi - r.lo) * 100) + '%;--hi:' + ((hi - r.lo) / (r.hi - r.lo) * 100) + '%"><div class="rng-track"><i class="rng-fill"></i></div>' +
        '<input type="range" class="wz-min" aria-label="حداقل قیمت" min="' + r.lo + '" max="' + r.hi + '" step="' + r.step + '" value="' + lo + '">' +
        '<input type="range" class="wz-max" aria-label="حداکثر قیمت" min="' + r.lo + '" max="' + r.hi + '" step="' + r.step + '" value="' + hi + '"></div>' +
      '<div class="rng-vals"><span>از <b class="wz-minL">' + api.fa(lo) + '</b></span><span>تا <b class="wz-maxL">' + api.fa(hi) + '</b> تومان</span></div>' +
      wzFoot(edit) + '</div>';
  }
  /* برند: کاشی با لوگو، تعداد مدل و کمترین قیمت؛ چندتایی + «فرقی نمی‌کنه» */
  function wzBrand(w, edit) {
    var bs = api.brands(w.cat), sel = w.brands || [];
    return '<div class="wz" data-wz="brand"><p class="wz-q">برند خاصی مدنظرته؟ <small>(چندتا هم می‌شه)</small></p><div class="wz-brands">' +
      bs.map(function (b) {
        return '<button type="button" class="wz-brand" data-wz-brand="' + esc(b.brand) + '" aria-pressed="' + (sel.indexOf(b.brand) > -1) + '"><span class="wz-logo">' + b.logo + '</span><b>' + esc(b.brand) + '</b>' +
          '<small>' + api.fa(b.models) + ' مدل' + (b.min ? ' · از ' + money(b.min) : '') + '</small><i class="wz-ck">' + api.icons.check + '</i></button>';
      }).join('') +
      '<button type="button" class="wz-brand any" data-wz-anybrand aria-pressed="' + (edit && !sel.length) + '"><span class="wz-logo any">؟</span><b>فرقی نمی‌کنه</b><small>همهٔ برندها</small><i class="wz-ck">' + api.icons.check + '</i></button>' +
      '</div>' + wzFoot(edit) + '</div>';
  }
  /* رفت‌وآمد: با چی می‌ری و زمان رسیدن چقدر برات مهمه */
  function wzTravel(w, edit) {
    var cur = w.mode || 'auto', mm = w.maxMin || 0;
    return '<div class="wz" data-wz="travel"><p class="wz-q">با چی می‌ری؟</p><div class="wz-opts wz-modes">' +
      ['car', 'moto', 'transit', 'walk', 'auto'].map(function (id) { return optBtn('data-wz-mode', id, cur === id, api.icons[id] + '<span>' + api.travelLabel(id) + '</span>'); }).join('') + '</div>' +
      '<p class="wz-q sub">زمان رسیدن چقدر برات مهمه؟</p><div class="wz-opts">' +
      [[15, 'حداکثر ۱۵ دقیقه'], [30, 'حداکثر ۳۰ دقیقه'], [45, 'حداکثر ۴۵ دقیقه'], [0, 'مهم نیست']].map(function (x) { return optBtn('data-wz-min', x[0], (edit || w.maxMin != null) && mm === x[0], x[1]); }).join('') + '</div>' +
      wzFoot(edit) + '</div>';
  }
  /* نزدیکی: فروشگاه نزدیک خانه/موقعیت فعلی باشد؟ */
  function wzNear(w, edit) {
    var k = w.nearKm || 0;
    return '<div class="wz" data-wz="near"><p class="wz-q">برات مهمه نزدیک خونه یا جای فعلیت باشه؟</p><div class="wz-opts wz-near">' +
      [[2, 'خیلی مهمه', 'تا ۲ کیلومتر'], [5, 'یه کم مهمه', 'تا ۵ کیلومتر'], [0, 'مهم نیست', 'همهٔ شهر']].map(function (x) {
        return optBtn('data-wz-near', x[0], (edit || w.nearKm != null) && k === x[0], '<b>' + x[1] + '</b><small>' + x[2] + '</small>');
      }).join('') + '</div><p class="wz-hint">فاصله از نقطهٔ «شما» روی نقشه حساب می‌شود؛ برای عوض کردنش، آن را روی نقشه بکشید.</p>' + wzFoot(edit) + '</div>';
  }
  function wzWidget(step, w, edit) { return { budget: wzBudget, brand: wzBrand, travel: wzTravel, near: wzNear }[step](w, edit); }
  function nextStep(step, w) {
    for (var i = WZ_STEPS.indexOf(step) + 1; i < WZ_STEPS.length; i++) {
      if (WZ_STEPS[i] === 'brand' && api.brands(w.cat).length < 2) continue;
      return WZ_STEPS[i];
    }
    return null;
  }
  /* مقدار ویجت از خود DOM خوانده می‌شود */
  function readWz(el, w) {
    var step = el.getAttribute('data-wz'), on = function (a) { var b = el.querySelector('[' + a + '][aria-pressed="true"]'); return b ? b.getAttribute(a) : null; };
    if (step === 'budget') {
      if (el.getAttribute('data-any') === '1') { w.budget = null; return; }
      var lo = +el.getAttribute('data-lo'), hi = +el.getAttribute('data-hi'), mn = +el.querySelector('.wz-min').value, mx = +el.querySelector('.wz-max').value;
      w.budget = mn <= lo && mx >= hi ? null : { min: mn > lo ? mn : 0, max: mx < hi ? mx : 0 };
    } else if (step === 'brand') {
      w.brands = Array.prototype.map.call(el.querySelectorAll('[data-wz-brand][aria-pressed="true"]'), function (b) { return b.getAttribute('data-wz-brand'); });
    } else if (step === 'travel') {
      w.mode = on('data-wz-mode') || 'auto'; w.maxMin = +(on('data-wz-min') || 0);
    } else w.nearKm = +(on('data-wz-near') || 0);
  }
  /* پیشنهاد نهایی: نوار فیلتر (هر چیپ همان ویجت را برای تغییر باز می‌کند)، کارت فروشگاه‌ها با گزینهٔ مقایسه */
  function finalCard(w) {
    var res = api.recommend(w), offs = res.offers.slice(0, MAX_ITEMS), cat = api.catById(w.cat);
    var chips = WZ_STEPS.filter(function (st) { return st !== 'brand' || api.brands(w.cat).length > 1; }).map(function (st) {
      return '<button type="button" class="wz-chip" data-wz-edit="' + st + '" aria-expanded="false">' + esc(wzSummary(st, w)) + '<i aria-hidden="true">✎</i></button>';
    }).join('');
    return '<article class="wz-final" data-wzf="' + esc(JSON.stringify(w)) + '">' +
      '<div class="wz-f-h"><b>پیشنهاد نهایی · ' + esc(cat ? cat.name : '') + '</b><small>' + (offs.length ? api.fa(res.offers.length) + ' فروشگاه با شرط‌های تو' + (res.offers.length > offs.length ? ' · ' + api.fa(offs.length) + ' تای بهتر' : '') : 'چیزی پیدا نشد') + '</small></div>' +
      (res.relaxed && offs.length ? '<p class="wz-note">با همهٔ شرط‌ها دقیقاً چیزی نبود؛ نزدیک‌ترین گزینه‌ها رو آوردم. شرط‌ها رو از نوار بالا عوض کن.</p>' : '') +
      '<div class="wz-fbar" role="group" aria-label="فیلترها (برای تغییر بزنید)">' + chips + '</div>' +
      '<div class="wz-editor" hidden></div>' +
      (offs.length ? '<div class="ag-cards wz-res">' + offs.map(function (o) { return offerCard(o, w.cat, { cmp: true, mode: o.tmode }); }).join('') + '</div>' : '<p class="wz-note">یکی از شرط‌ها رو شل‌تر کن (مثلاً بودجه یا نزدیکی).</p>') +
      '<div class="wz-cmpbar" hidden><span class="wz-cmpn"></span><button type="button" class="ag-pick" data-wz-cmp>مقایسه در چت</button><button type="button" class="ag-go" data-wz-cmpfull>جدول کامل</button></div>' +
    '</article>';
  }
  /* مقایسهٔ جمع‌وجور چند فروشگاه در چت: قیمت، فاصله، زمان رسیدن، امتیاز، ضمانت؛ بهترین‌ها سبز */
  function offerCmpCard(list, mode) {
    var d = api.offerCompare(list, mode), n = d.cols.length, keep = ['قیمت', 'فاصله', 'زمان رسیدن', 'امتیاز فروشگاه', 'ضمانت ترب'];
    var rows = d.rows.filter(function (r) { return keep.indexOf(r.l) > -1; });
    return '<article class="ag-cmp ag-ocmp n' + n + '" role="button" tabindex="0" data-ocmp="' + esc(JSON.stringify({ list: list, mode: mode })) + '" aria-label="جدول کامل مقایسهٔ فروشگاه‌ها">' +
      '<div class="ag-cmp-scroll"><div class="ag-cmp-in" style="--n:' + n + '">' +
        '<div class="ag-cmp-heads">' + d.cols.map(function (c, i) {
          return '<div class="ag-cmp-p"><span class="ag-cmp-img">' + c.art + '<b class="nb nb-' + (i + 1) + '">' + api.fa(i + 1) + '</b></span><b>' + esc(c.name) + '</b><small>' + esc(api.model(c.title)) + '</small></div>';
        }).join('') + '</div>' +
        '<ul class="ag-cmp-rows">' + rows.map(function (r) {
          return '<li><span class="ag-cr-l">' + esc(r.l) + '</span><span class="ag-cr-vs">' + r.v.map(function (v, i) { return '<span class="ag-cr-v' + ((r.win || []).indexOf(i) > -1 ? ' win' : '') + '">' + esc(v) + '</span>'; }).join('') + '</span></li>';
        }).join('') + '</ul>' +
      '</div></div><span class="ag-cmp-more">' + api.icons.expand + 'جدول کامل مقایسه</span></article>';
  }
  function selectedOffers(fin) {
    return Array.prototype.map.call(fin.querySelectorAll('[data-csel]:checked'), function (c) { var x = c.getAttribute('data-csel').split('|'); return { sid: x[0], cat: x[1], title: x.slice(2).join('|') }; });
  }

  /* ================= راهنمای رسیدن به فروشگاه ================= */
  function guideMap(g) {
    /* کاربر دور است ← فقط اطراف فروشگاه و نشانه‌ها (با نام) دیده شود؛ نزدیک است ← مسیر از «شما» هم */
    var W = 320, H = 150, P = 26, pts = [{ lat: g.lat, lng: g.lng }].concat(g.close ? [g.origin] : []).concat(g.marks), kx = Math.cos(35.7 * Math.PI / 180);
    var minX = Math.min.apply(null, pts.map(function (p) { return p.lng * kx; })), maxX = Math.max.apply(null, pts.map(function (p) { return p.lng * kx; }));
    var minY = Math.min.apply(null, pts.map(function (p) { return p.lat; })), maxY = Math.max.apply(null, pts.map(function (p) { return p.lat; }));
    var sc = Math.min((W - 2 * P) / ((maxX - minX) || 1e-3), (H - 2 * P) / ((maxY - minY) || 1e-3));
    var ox = (W - (maxX - minX) * sc) / 2, oy = (H - (maxY - minY) * sc) / 2;
    function X(p) { return (ox + (p.lng * kx - minX) * sc).toFixed(1); }
    function Y(p) { return (oy + (maxY - p.lat) * sc).toFixed(1); }
    var s = '';
    for (var i = 1; i < 6; i++) s += '<path d="M0 ' + (i * H / 6) + 'H' + W + 'M' + (i * W / 6) + ' 0V' + H + '" class="am-grid"/>';
    if (g.close) s += '<path d="M' + X(g.origin) + ' ' + Y(g.origin) + 'L' + X(g) + ' ' + Y(g) + '" class="am-route"/>';
    g.marks.forEach(function (m, i) {
      s += '<circle cx="' + X(m) + '" cy="' + Y(m) + '" r="4" class="am-mark ' + m.kind + '"/>';
      if (i < 3) s += '<text x="' + X(m) + '" y="' + (+Y(m) - 8) + '" class="am-label" text-anchor="middle">' + esc(m.name.length > 18 ? m.name.slice(0, 17) + '…' : m.name) + '</text>';
    });
    if (g.close) s += '<circle cx="' + X(g.origin) + '" cy="' + Y(g.origin) + '" r="5.5" class="am-you"/>';
    s += '<path d="M' + X(g) + ' ' + Y(g) + 'm0 0c-6-8-9-11-9-15a9 9 0 0 1 18 0c0 4-3 7-9 15z" class="am-pin"/>';
    return '<svg class="ag-amap" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid slice" aria-hidden="true">' + s + '</svg>';
  }
  function guideCard(g) {
    var li = function (ic, html, cls) { return '<li' + (cls ? ' class="' + cls + '"' : '') + '><span class="ag-g-ic" aria-hidden="true">' + ic + '</span><span>' + html + '</span></li>'; };
    return '<article class="ag-guide">' +
      '<div class="ag-st-top"><span class="ag-st-img" aria-hidden="true">' + g.art + '</span><div class="ag-st-h"><b class="ag-c-name">' + esc(g.name) + '</b><small class="ostat ' + g.statusK + '">' + esc(g.status) + '</small></div></div>' +
      '<button type="button" class="ag-amap-btn" data-ag-smap="' + g.sid + '" aria-label="روی نقشه">' + guideMap(g) + '<span class="ag-amap-tag">' + api.icons.map + 'روی نقشه</span></button>' +
      '<ul class="ag-g-list">' +
        li(api.icons.pin, esc(g.addr)) +
        (g.bits.length ? li('🏢', 'ورودی: ' + esc(g.bits.join('، '))) : '') +
        li('🧭', esc(g.from) + ' · پیاده ' + api.fa(g.walk) + ' دقیقه · ماشین ' + api.fa(g.car) + ' دقیقه') +
        g.lines.map(function (l) { return li('📍', 'نشانه: ' + esc(l), 'lm'); }).join('') +
      '</ul>' +
      (g.tips.length ? '<ol class="ag-g-tips">' + g.tips.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ol>' : '') +
      '<div class="ag-c-acts"><a class="ag-pick" href="' + esc(g.route) + '" target="_blank" rel="noopener">' + api.icons.route + 'مسیریابی</a>' +
        '<button type="button" class="ag-go" data-ag-call="' + g.sid + '">' + api.icons.phone + 'تماس</button></div>' +
      (g.level > 1 ? '<button type="button" class="ag-lost" data-ag-locate>' + api.icons.pin + 'موقعیتم رو به‌روز کن</button>'
                   : '<button type="button" class="ag-lost" data-ag-ask="گم شدم، «' + esc(g.name) + '» رو پیدا نمی‌کنم">گم شدم / پیداش نمی‌کنم</button>') +
    '</article>';
  }

  /* ================= خلاصهٔ استعلام‌ها در گفتگو ================= */
  function inqCard() {
    var list = api.inquiries().slice(0, 3);
    return '<div class="ag-inq">' + list.map(function (q) {
      var st = api.storeInfo(q.sid);
      return '<div class="ag-iq-row"><span class="ag-c-art" aria-hidden="true">' + st.art + '</span><div class="ag-er-t"><b>' + esc(st.name) + '</b><small>' + esc(api.model(q.title) || q.title) + '</small></div>' +
        (q.status === 'answered' && q.answer ? '<b class="ag-iq-price">' + api.fa(q.answer.price) + '</b>' : '') + '<span class="iq-badge ' + api.inqBadge(q).cls + '">' + api.inqBadge(q).label + '</span></div>';
    }).join('') + '<button type="button" class="ag-pick" data-ag-view="inq">همهٔ استعلام‌ها</button></div>';
  }

  function replyHTML(r) {
    var h = '<p class="ag-t">' + esc(r.text).replace(/\n/g, '<br>') + '</p>';
    if (r.compare) h += compareCard(r.compare);
    if (r.wizard) h += wzWidget('budget', NQ.AgentBrain.state().wiz || r.wizard, false);
    if (r.guide) h += guideCard(r.guide);
    if (r.inq && api.inquiries().length) h += inqCard();
    if (r.area && r.area.data.sids.length) h += areaCard(r);
    var sellers = r.area ? r.area.data.stores.slice(0, MAX_ITEMS) : r.stores;
    if (sellers.length) h += '<div class="ag-group"><div class="ag-cards">' + sellers.map(sellerCard).join('') + '</div></div>';
    r.products.forEach(function (g) { h += '<div class="ag-group"><div class="ag-cards">' + g.items.map(productCard).join('') + '</div></div>'; });
    r.groups.forEach(function (g) {
      h += '<div class="ag-group">' + (r.groups.length > 1 || g.note ? '<p class="ag-g-h">' + esc(g.label) + (g.note ? ' <small>' + esc(g.note) + '</small>' : '') + '</p>' : '') +
        '<div class="ag-cards">' + g.offers.map(function (o) { return offerCard(o, g.cat); }).join('') + '</div></div>';
    });
    if (r.route) h += '<button type="button" class="ag-route-in" data-ag-route>' + api.icons.route + 'بچین برام</button>';
    return h + chipsHTML(r.follow);
  }

  /* ---- گفتگوهای قبلی (فعلاً در مرورگر ذخیره می‌شوند؛ بعداً از حساب کاربری خوانده می‌شوند) ---- */
  function loadChats() { try { chats = JSON.parse(localStorage.getItem(CHAT_KEY) || '[]') || []; } catch (e) { chats = []; } }
  function storeChats() { try { localStorage.setItem(CHAT_KEY, JSON.stringify(chats.slice(0, MAX_CHATS))); } catch (e) {} }
  function saveCurrent() {
    if (!logEl.querySelector('.ag-msg.me')) return;
    var first = logEl.querySelector('.ag-msg.me .ag-t'), c = chats.filter(function (x) { return x.id === curId; })[0];
    if (!c) { curId = curId || 'c' + Date.now(); c = { id: curId }; chats.unshift(c); }
    c.title = (first ? first.textContent : 'گفتگو').slice(0, 60);
    c.at = Date.now(); c.html = logEl.innerHTML; c.errands = errands; c.seq = seq; c.ctx = NQ.AgentBrain.state();
    chats.sort(function (a, b) { return b.at - a.at; });
    storeChats(); renderHist();
  }
  function dayLabel(t) {
    var now = new Date(), day0 = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    if (t >= day0) return 'امروز';
    if (t >= day0 - 864e5) return 'دیروز';
    if (t >= day0 - 7 * 864e5) return 'هفتهٔ گذشته';
    return 'قبل‌تر';
  }
  function renderHist() {
    var el = $('#agHList'), last = '';
    if (!chats.length) { el.innerHTML = '<li class="ag-hempty">هنوز گفتگویی نداری.</li>'; return; }
    el.innerHTML = chats.map(function (c) {
      var g = dayLabel(c.at), h = g !== last ? '<li class="ag-hgrp">' + g + '</li>' : '';
      last = g;
      return h + '<li class="ag-hi' + (c.id === curId ? ' on' : '') + '"><button type="button" class="ag-hopen" data-chat="' + c.id + '"' + (c.id === curId ? ' aria-current="true"' : '') + '>' + esc(c.title) + '</button>' +
        '<button type="button" class="ag-hdel" data-chat-del="' + c.id + '" aria-label="حذف گفتگو: ' + esc(c.title) + '" title="حذف">×</button></li>';
    }).join('');
  }
  function openChat(id) {
    var c = chats.filter(function (x) { return x.id === id; })[0]; if (!c) return;
    curId = c.id; logEl.innerHTML = c.html || ''; errands = (c.errands || []).filter(function (e) { return !e.cat; }); seq = c.seq || 0;
    NQ.AgentBrain.load(c.ctx); renderVisits(); syncPicks(); renderHist(); syncEmpty(); scrollEnd(); closeHist();
  }
  function newChat() {
    curId = null; logEl.innerHTML = ''; errands = []; seq = 0; NQ.AgentBrain.reset();
    renderVisits(); renderHist(); syncEmpty(); closeHist(); inputEl.value = ''; syncSend(); inputEl.focus();
  }
  function setRail(on, quiet) {
    agentEl.classList.toggle('hist-rail', on);
    var b = $('#agHToggle'), lbl = on ? 'باز کردن نوار کناری' : 'بستن نوار کناری';
    b.setAttribute('aria-expanded', String(!on)); b.setAttribute('aria-label', lbl); b.title = lbl;
    if (!quiet) try { localStorage.setItem('nq-hist-rail', on ? '1' : '0'); } catch (e) {}
  }
  function openHist() {
    agentEl.classList.add('hist-open'); $('#agScrim').hidden = false; $('#histBtn').setAttribute('aria-expanded', 'true');
    var f = $('#agHList .ag-hopen') || $('#agHNew'); f.focus();
  }
  function closeHist() {
    if (!agentEl.classList.contains('hist-open')) return;
    agentEl.classList.remove('hist-open'); $('#agScrim').hidden = true; $('#histBtn').setAttribute('aria-expanded', 'false');
  }

  /* ---- سر زدن‌ها: برنامهٔ سر زدن (فروشگاه‌های انتخاب‌شده، از قبل هم) + کالاهایی که هنوز در ترب‌مپ نیستند ----
     هر ردیف انتخاب‌شدنی است؛ «سر زدم» و «پاک کردن» روی انتخاب‌شده‌ها، و «پاک کردن همه». */
  var vsel = {}, vopen = {};   // ردیف‌های انتخاب‌شده / ردیف‌هایی که جزئیاتشان باز است (s:شناسهٔ فروشگاه یا e:شمارهٔ کالا)
  function addErrands(r) {
    /* فروشگاه‌ها خودکار اضافه نمی‌شوند (فقط با «انتخاب»)؛ کالاهایی که در ترب‌مپ نیستند یادداشت می‌شوند */
    r.missing.forEach(function (m) {
      if (errands.some(function (e) { return e.label === m; })) return;
      errands.push({ id: ++seq, label: m, done: false });
    });
    renderVisits();
  }
  function visitRows() {
    return api.plan.list().map(function (st) { return { key: 's:' + st.sid, st: st, done: st.done }; })
      .concat(errands.map(function (e) { return { key: 'e:' + e.id, er: e, done: e.done }; }));
  }
  function renderVisits() {
    var rows = visitRows(), n = rows.length, active = rows.filter(function (r) { return r.st && !r.done; }).length;
    Object.keys(vsel).forEach(function (k) { if (!rows.some(function (r) { return r.key === k; })) delete vsel[k]; });
    var nsel = Object.keys(vsel).length;
    $('#agCount').textContent = api.fa(n);
    var vc = $('#visitsCnt'); vc.hidden = !n; vc.textContent = api.fa(n);
    $('#agSideNote').hidden = n > 0;
    $('#agVTools').hidden = !n;
    $('#agVAll').checked = n > 0 && nsel === n; $('#agVAll').indeterminate = nsel > 0 && nsel < n;
    Array.prototype.forEach.call(document.querySelectorAll('#agVTools [data-v="done"],#agVTools [data-v="rm"]'), function (b) { b.disabled = !nsel; });
    var sum = api.plan.summary(), sm = $('#agVSum');
    sm.hidden = !sum; sm.innerHTML = sum ? '<span>' + sum + '</span><button type="button" class="link-btn" data-vlist>دیدن در فهرست</button>' : '';
    $('#agErrands').innerHTML = rows.map(function (r) {
      var on = !!vsel[r.key], open = !!vopen[r.key], head, det = '';
      if (r.st) {
        var st = r.st;
        head = '<span class="ag-v-art" aria-hidden="true">' + (st.n && !st.done ? '<b class="ag-v-n">' + api.fa(st.n) + '</b>' : '') + st.art + '</span>' +
          '<button type="button" class="ag-v-main" data-vopen="' + r.key + '" aria-expanded="' + open + '"><b>' + esc(st.name) + '</b><small>' +
            (st.status ? '<span class="ag-v-st ' + st.statusK + '">' + esc(st.status) + '</span> · ' : '') + st.items.map(function (x) { return esc(api.model(x.title) || x.label); }).join('، ') + '</small></button>';
        if (open) det = '<div class="ag-v-det">' +
          (st.arrive && !st.done ? '<p class="ag-v-leg">رسیدن حدود <b>' + st.arrive + '</b>' + (st.leg ? ' · ' + st.leg : '') + '</p>' : '') +
          '<ul class="ag-v-items">' + st.items.map(function (x) {
            return '<li><span class="ag-v-it">' + esc(x.title || x.label) + '</span>' + (x.stock ? '<span class="stock ' + x.stock + '">' + api.plan.stock[x.stock] + '</span>' : '') + (x.price ? '<b>' + api.fa(x.price) + ' <small>تومان</small></b>' : '') + '</li>';
          }).join('') + '</ul>' +
          '<p class="ag-v-addr">' + esc(st.addr) + ' · ساعت کار ' + esc(st.hours) + '</p>' +
          '<div class="ag-v-acts"><button type="button" class="ag-go" data-ag-store="' + st.sid + '" data-cat="' + (st.items[0] ? st.items[0].cat : '') + '" data-title="' + esc(st.items[0] ? st.items[0].title : '') + '">اطلاعات فروشگاه</button>' +
            '<button type="button" class="ag-go" data-vgo="list" data-sid="' + st.sid + '">در فهرست</button>' +
            '<button type="button" class="ag-go" data-vgo="map" data-sid="' + st.sid + '" aria-label="روی نقشه" title="روی نقشه">' + api.icons.map + '</button>' +
            '<button type="button" class="ag-go" data-ag-ask="چطوری برم «' + esc(st.name) + '»؟" aria-label="راهنمای رسیدن" title="راهنمای رسیدن">' + api.icons.route + '</button></div></div>';
      } else head = '<span class="ag-v-art miss" aria-hidden="true">؟</span><div class="ag-er-t"><b>' + esc(r.er.label) + '</b><small>فعلاً تو ترب‌مپ نیست</small></div>';
      return '<li class="ag-er' + (r.done ? ' done' : '') + (r.er ? ' missing' : '') + (on ? ' sel' : '') + (open ? ' open' : '') + '">' +
        '<label class="ag-v-ck"><input type="checkbox" data-vsel="' + r.key + '"' + (on ? ' checked' : '') + ' aria-label="انتخاب ' + esc(r.st ? r.st.name : r.er.label) + '"></label>' + head +
        '<button type="button" class="ag-v-done" data-vdone="' + r.key + '" aria-pressed="' + !!r.done + '" title="' + (r.done ? 'برگرداندن' : 'سر زدم') + '">' + api.icons.check + '<span>' + (r.done ? 'سر زدم' : 'سر زدم؟') + '</span></button>' +
        '<button type="button" class="ag-er-x" data-vrm="' + r.key + '" aria-label="حذف ' + esc(r.st ? r.st.name : r.er.label) + '">×</button>' + det + '</li>';
    }).join('');
    var rb = $('#agRoute');
    rb.disabled = !active;
    rb.innerHTML = api.icons.route + '<span>' + (active ? 'مسیر روی نقشه (' + api.fa(active) + ' فروشگاه)' : 'مسیر روی نقشه') + '</span>';
  }
  /* دکمه‌های «انتخاب» در گفتگو با برنامهٔ سر زدن هم‌خوان شوند (مثلاً بعد از باز کردن یک گفتگوی قدیمی) */
  function syncPicks() {
    Array.prototype.forEach.call(logEl.querySelectorAll('[data-ag-pick]'), function (b) {
      var on = api.plan.has(b.getAttribute('data-ag-pick'), b.getAttribute('data-cat'));
      if (b.getAttribute('aria-pressed') === String(on)) return;
      b.setAttribute('aria-pressed', String(on)); b.innerHTML = on ? api.icons.check + 'فهرست' : 'انتخاب';
      var card = b.closest('.ag-card'); if (card) card.classList.toggle('picked', on);
    });
  }
  function vAct(kind, keys) {
    keys.forEach(function (k) {
      var id = k.slice(2);
      if (k.charAt(0) === 's') {
        if (kind === 'rm') api.plan.remove(id);
        else { var st = api.plan.list().filter(function (x) { return x.sid === id; })[0]; api.plan.setDone(id, kind === 'toggle' ? !(st && st.done) : true); }
      } else {
        if (kind === 'rm') errands = errands.filter(function (e) { return e.id !== +id; });
        else errands.forEach(function (e) { if (e.id === +id) e.done = kind === 'toggle' ? !e.done : true; });
      }
      delete vsel[k];
    });
    renderVisits(); syncPicks(); saveCurrent();
  }
  function buildRoute() {
    if (!api.plan.list().some(function (s) { return !s.done; })) return;
    closeSide(); api.goPlan();
  }
  /* پنل سر زدن‌ها: دسکتاپ پهن ستون کناری (با دکمه پنهان/نمایان)، کوچک‌تر کشویی از چپ */
  function wideSide() { return window.matchMedia('(min-width:1100px)').matches; }
  function toggleSide() {
    if (wideSide()) { var off = !agentEl.classList.contains('side-off'); agentEl.classList.toggle('side-off', off); $('#visitsBtn').setAttribute('aria-expanded', String(!off)); try { localStorage.setItem('nq-side-off', off ? '1' : '0'); } catch (e) {} return; }
    if (agentEl.classList.contains('side-open')) closeSide(); else { closeHist(); agentEl.classList.add('side-open'); $('#agScrim').hidden = false; $('#visitsBtn').setAttribute('aria-expanded', 'true'); }
  }
  function closeSide() {
    if (!agentEl.classList.contains('side-open')) return;
    agentEl.classList.remove('side-open'); $('#agScrim').hidden = true; $('#visitsBtn').setAttribute('aria-expanded', 'false');
  }

  function pressOne(b) {
    Array.prototype.forEach.call(b.parentNode.querySelectorAll('.wz-opt'), function (x) { x.setAttribute('aria-pressed', String(x === b)); });
  }
  function syncRng(wz) {
    var mn = wz.querySelector('.wz-min'), mx = wz.querySelector('.wz-max'), lo = +mn.min, hi = +mn.max, sp = (hi - lo) || 1;
    var r = wz.querySelector('.wz-rng'); r.style.setProperty('--lo', ((+mn.value - lo) / sp * 100) + '%'); r.style.setProperty('--hi', ((+mx.value - lo) / sp * 100) + '%');
    wz.querySelector('.wz-minL').textContent = api.fa(+mn.value); wz.querySelector('.wz-maxL').textContent = api.fa(+mx.value);
  }
  /* تأیید یک ویجت: در جریان سؤال‌ها ← سؤال بعدی یا پیشنهاد نهایی؛ در نوار فیلتر پیشنهاد نهایی ← همان کارت به‌روز می‌شود */
  function wzSubmit(wz) {
    var step = wz.getAttribute('data-wz'), fin = wz.closest('.wz-final');
    if (fin) {
      var wf = JSON.parse(fin.getAttribute('data-wzf')); readWz(wz, wf);
      var box = document.createElement('div'); box.innerHTML = finalCard(wf);
      fin.parentNode.replaceChild(box.firstChild, fin);
      if (NQ.AgentBrain.state().wiz) NQ.AgentBrain.state().wiz = wf;
      saveCurrent(); return;
    }
    var ctxw = NQ.AgentBrain.state(), w = ctxw.wiz || { cat: ctxw.cats[0] };
    readWz(wz, w); ctxw.wiz = w;
    wz.classList.add('done');
    Array.prototype.forEach.call(wz.querySelectorAll('button,input'), function (x) { x.disabled = true; });
    bubble('me', '<p class="ag-t">' + esc(wzSummary(step, w)) + '</p>');
    var nx = nextStep(step, w);
    if (nx) bubble('bot', wzWidget(nx, w, false));   // خود ویجت سؤال را می‌پرسد
    else bubble('bot', '<p class="ag-t">اینا بهترین فروشگاه‌ها با شرط‌های تو هستن. هر شرطی رو خواستی از نوار بالا عوض کن؛ برای مقایسه، تیک «مقایسه» رو بزن.</p>' + finalCard(w));
    saveCurrent();
  }
  function syncSend() { $('#agSend').disabled = busy || !inputEl.value.trim(); }
  function ask(text) {
    text = String(text || '').trim();
    if (!text || busy) return;
    busy = true; syncSend();
    bubble('me', '<p class="ag-t">' + esc(text) + '</p>');
    var typing = bubble('bot typing', '<span class="ag-dots"><i></i><i></i><i></i></span>');
    setTimeout(function () {
      var r = NQ.AgentBrain.respond(text, api);
      /* درخواست خارج از کاتالوگ نمونه ← دستیار هوشمند بک‌اند ترب روی کاتالوگ واقعی */
      /* پاسخ به سؤال تکمیلی دستیار بک‌اند (مثلاً بودجه) هم به همان گفتگو می‌رود */
      var viaBk = NQ.Backend && (r.unknown || NQ.Backend.awaitingAnswer || (NQ.Backend.active && !api.findCat(text) && !api.findProducts(text).length));
      if (NQ.Backend) NQ.Backend.active = !!viaBk;
      if (viaBk) {
        NQ.Backend.chat(text).then(function (html) {
          typing.classList.remove('typing');
          typing.querySelector('.ag-b').innerHTML = html || replyHTML(r);
          if (!html) addErrands(r);
          busy = false; syncSend(); scrollEnd(); saveCurrent();
        });
        return;
      }
      typing.classList.remove('typing');
      typing.querySelector('.ag-b').innerHTML = replyHTML(r);
      addErrands(r);
      busy = false; syncSend(); scrollEnd(); saveCurrent();
    }, 650);
  }

  NQ.AgentUI = {
    init: function (a) {
      api = a;
      agentEl = $('#agent'); logEl = $('#agLog'); inputEl = $('#agInput');
      $('#agSend').innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M6 11l6-6 6 6"/></svg>';
      $('#agMic').innerHTML = api.icons.mic;
      $('.ag-hello').insertAdjacentHTML('beforeend', chipsHTML(SUGGEST));
      loadChats(); renderHist(); renderVisits(); syncEmpty();
      try { if (localStorage.getItem('nq-side-off') === '1') { agentEl.classList.add('side-off'); $('#visitsBtn').setAttribute('aria-expanded', 'false'); } } catch (e) {}
      if (!wideSide()) $('#visitsBtn').setAttribute('aria-expanded', 'false');
      $('#visitsBtn').addEventListener('click', toggleSide);
      $('#agSideClose').addEventListener('click', function () { if (wideSide()) toggleSide(); else closeSide(); });
      $('#agVAll').addEventListener('change', function () {
        var on = this.checked; vsel = {};
        if (on) visitRows().forEach(function (r) { vsel[r.key] = 1; });
        renderVisits();
      });
      $('#agVTools').addEventListener('click', function (e) {
        var b = e.target.closest('[data-v]'); if (!b || b.disabled) return;
        var k = b.getAttribute('data-v');
        if (k === 'clear') {
          if (!window.confirm('همهٔ سر زدن‌ها (برنامهٔ سر زدن و یادداشت‌ها) پاک شوند؟')) return;
          api.plan.clear(); errands = []; vsel = {}; renderVisits(); syncPicks(); saveCurrent(); return;
        }
        vAct(k === 'done' ? 'done' : 'rm', Object.keys(vsel));
      });
      /* انتخاب فروشگاه برای مقایسه در پیشنهاد نهایی (حداکثر ۵) */
      agentEl.addEventListener('change', function (e) {
        var c = e.target.closest && e.target.closest('[data-csel]'); if (!c) return;
        var fin = c.closest('.wz-final'), n = fin.querySelectorAll('[data-csel]:checked').length;
        if (n > 5) { c.checked = false; api.toast('حداکثر ۵ فروشگاه را می‌شود با هم مقایسه کرد.', 'warn'); n = 5; }
        var bar = fin.querySelector('.wz-cmpbar'); bar.hidden = n < 2;
        bar.querySelector('.wz-cmpn').textContent = api.fa(n) + ' فروشگاه انتخاب شده';
        c.closest('.ag-card').classList.toggle('csel', c.checked);
      });
      /* دستگیره‌های بازهٔ قیمت */
      agentEl.addEventListener('input', function (e) {
        if (!e.target.classList || !(e.target.classList.contains('wz-min') || e.target.classList.contains('wz-max'))) return;
        var wz = e.target.closest('.wz'), mn = wz.querySelector('.wz-min'), mx = wz.querySelector('.wz-max'), step = +mn.step;
        if (e.target === mn && +mn.value > +mx.value - step) mn.value = +mx.value - step;
        if (e.target === mx && +mx.value < +mn.value + step) mx.value = +mn.value + step;
        wz.setAttribute('data-any', '0');
        Array.prototype.forEach.call(wz.querySelectorAll('[data-wz-preset]'), function (b) { b.setAttribute('aria-pressed', 'false'); });
        syncRng(wz);
      });
      $('#agErrands').addEventListener('change', function (e) {
        var k = e.target.getAttribute('data-vsel'); if (!k) return;
        if (e.target.checked) vsel[k] = 1; else delete vsel[k];
        renderVisits();
      });
      $('#agForm').addEventListener('submit', function (e) { e.preventDefault(); var v = inputEl.value; inputEl.value = ''; ask(v); syncSend(); });
      inputEl.addEventListener('input', syncSend);
      $('#agRoute').addEventListener('click', buildRoute);
      $('#agHNew').addEventListener('click', newChat);
      $('#newChatBtn').addEventListener('click', newChat);
      $('#histBtn').addEventListener('click', function () { if (agentEl.classList.contains('hist-open')) closeHist(); else openHist(); });
      /* دسکتاپ: نوار کناری باز یا جمع‌شده (فقط آیکون‌ها)؛ انتخاب کاربر یادش می‌ماند */
      var rail = null;
      try { rail = localStorage.getItem('nq-hist-rail'); } catch (e) {}
      setRail(rail == null ? window.innerWidth < 1100 : rail === '1', true);
      $('#agHToggle').addEventListener('click', function () { setRail(!agentEl.classList.contains('hist-rail')); });
      $('#agHClose').addEventListener('click', closeHist);
      $('#agScrim').addEventListener('click', function () { closeHist(); closeSide(); });
      document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { closeHist(); closeSide(); } });
      agentEl.addEventListener('keydown', function (e) {   // کارت مقایسه با Enter/فاصله هم باز می‌شود
        var t = e.target.closest && e.target.closest('[data-ag-cmp]');
        if (t && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); t.click(); }
      });
      agentEl.addEventListener('click', function (e) {
        var t;
        if ((t = e.target.closest('[data-chat]'))) { openChat(t.getAttribute('data-chat')); return; }
        if ((t = e.target.closest('[data-chat-del]'))) {
          var id = t.getAttribute('data-chat-del');
          chats = chats.filter(function (x) { return x.id !== id; }); storeChats();
          if (id === curId) newChat(); else renderHist();
          return;
        }
        if ((t = e.target.closest('[data-ag-ask]'))) { ask(t.getAttribute('data-ag-ask')); return; }
        /* ویجت‌ها: گزینه‌های تک‌انتخابی، برند چندانتخابی، میان‌بُرهای قیمت */
        if ((t = e.target.closest('[data-wz-preset]'))) {
          var wz = t.closest('.wz'), pv = t.getAttribute('data-wz-preset');
          pressOne(t);
          wz.setAttribute('data-any', pv === 'any' ? '1' : '0');
          if (pv !== 'any') { var pr = pv.split(','); wz.querySelector('.wz-min').value = pr[0]; wz.querySelector('.wz-max').value = pr[1]; syncRng(wz); }
          return;
        }
        if ((t = e.target.closest('[data-wz-mode],[data-wz-min],[data-wz-near]'))) { pressOne(t); return; }
        if ((t = e.target.closest('[data-wz-brand]'))) {
          t.setAttribute('aria-pressed', String(t.getAttribute('aria-pressed') !== 'true'));
          var any = t.closest('.wz').querySelector('[data-wz-anybrand]'); if (any) any.setAttribute('aria-pressed', 'false');
          return;
        }
        if ((t = e.target.closest('[data-wz-anybrand]'))) {
          Array.prototype.forEach.call(t.closest('.wz').querySelectorAll('[data-wz-brand]'), function (b) { b.setAttribute('aria-pressed', 'false'); });
          t.setAttribute('aria-pressed', 'true'); return;
        }
        if ((t = e.target.closest('[data-wz-ok]'))) { wzSubmit(t.closest('.wz')); return; }
        if ((t = e.target.closest('[data-wz-edit]'))) {
          var fin = t.closest('.wz-final'), ed = fin.querySelector('.wz-editor'), step = t.getAttribute('data-wz-edit'), open = t.getAttribute('aria-expanded') === 'true';
          Array.prototype.forEach.call(fin.querySelectorAll('[data-wz-edit]'), function (c) { c.setAttribute('aria-expanded', 'false'); });
          if (open) { ed.hidden = true; ed.innerHTML = ''; return; }
          t.setAttribute('aria-expanded', 'true');
          ed.innerHTML = wzWidget(step, JSON.parse(fin.getAttribute('data-wzf')), true); ed.hidden = false;
          return;
        }
        if ((t = e.target.closest('[data-wz-cmp],[data-wz-cmpfull]'))) {
          var f2 = t.closest('.wz-final'), list = selectedOffers(f2), wv = JSON.parse(f2.getAttribute('data-wzf'));
          if (list.length < 2) return;
          if (t.hasAttribute('data-wz-cmpfull')) { api.openOfferCompare(list, wv.mode); return; }
          bubble('me', '<p class="ag-t">مقایسهٔ ' + api.fa(list.length) + ' فروشگاه انتخاب‌شده</p>');
          var bm = bubble('bot', '<p class="ag-t">اینم مقایسهٔ فروشگاه‌هایی که انتخاب کردی (سبز = بهتر):</p>' + offerCmpCard(list, wv.mode));
          saveCurrent(); return;
        }
        if ((t = e.target.closest('[data-ocmp]'))) { var oc = JSON.parse(t.getAttribute('data-ocmp')); api.openOfferCompare(oc.list, oc.mode); return; }
        if ((t = e.target.closest('[data-ag-call]'))) { api.callStore(t.getAttribute('data-ag-call')); return; }
        if (e.target.closest('[data-ag-locate]')) { api.locate(); return; }
        if ((t = e.target.closest('[data-ag-view]'))) { api.goView(t.getAttribute('data-ag-view')); return; }
        if ((t = e.target.closest('[data-ag-cmp]'))) {
          var c = t.getAttribute('data-ag-cmp').split('|');   // «دسته|id1,id2,...» (گفتگوهای قدیمی: «دسته|a|b»)
          api.openCompare(c[0], (c.length > 2 ? c.slice(1) : c[1].split(','))); return;
        }
        if ((t = e.target.closest('[data-ag-store]'))) { api.storeDialog(t.getAttribute('data-ag-store'), t.getAttribute('data-cat'), t.getAttribute('data-title')); return; }
        if ((t = e.target.closest('[data-ag-smap]'))) { api.storeOnMap(t.getAttribute('data-ag-smap')); return; }
        if ((t = e.target.closest('[data-ag-area]'))) {
          var aq = {}; try { aq = JSON.parse(t.getAttribute('data-q')); } catch (er) {}
          api.showArea(api.area(aq), t.getAttribute('data-ag-area')); return;
        }
        if (e.target.closest('[data-ag-route]')) { buildRoute(); return; }
        if ((t = e.target.closest('[data-ag-open]'))) { api.openStore(t.getAttribute('data-cat'), t.getAttribute('data-sid'), t.getAttribute('data-title'), t.getAttribute('data-ag-open')); return; }
        if ((t = e.target.closest('[data-ag-pick]'))) {   // «انتخاب» = افزودن/برداشتن از سر زدن‌ها
          var on = api.plan.toggle(t.getAttribute('data-ag-pick'), t.getAttribute('data-cat'));
          if (on) api.toast('به سر زدن‌ها اضافه شد.', 'success');
          syncPicks(); renderVisits(); saveCurrent(); return;
        }
        if ((t = e.target.closest('[data-vdone]'))) { vAct('toggle', [t.getAttribute('data-vdone')]); return; }
        if ((t = e.target.closest('[data-vopen]'))) { var vk = t.getAttribute('data-vopen'); if (vopen[vk]) delete vopen[vk]; else vopen[vk] = 1; renderVisits(); var b0 = agentEl.querySelector('[data-vopen="' + vk + '"]'); if (b0) b0.focus({ preventScroll: true }); return; }
        if ((t = e.target.closest('[data-vgo]'))) { closeSide(); api.plan.open(t.getAttribute('data-sid'), t.getAttribute('data-vgo')); return; }
        if (e.target.closest('[data-vlist]')) { closeSide(); api.plan.open(null, 'list'); return; }
        if ((t = e.target.closest('[data-vrm]'))) { vAct('rm', [t.getAttribute('data-vrm')]); return; }
      });
    },
    onShow: function () { scrollEnd(); },
    onHide: function () { closeHist(); closeSide(); },
    /* برنامهٔ سر زدن در فهرست یا نقشه عوض شد */
    sync: function () { if (!api || !agentEl) return; renderVisits(); syncPicks(); },
    /* برای «پاک کردن گفتگوها» در تنظیمات */
    clearAll: function () { chats = []; storeChats(); newChat(); },
    /* «راهنمای رسیدن» از پنجرهٔ فروشگاه */
    askGuide: function (sid) { var st = api.storeInfo(sid); setTimeout(function () { ask('چطوری برم «' + st.name + '»؟'); }, 60); }
  };
})(window.NQ = window.NQ || {});
