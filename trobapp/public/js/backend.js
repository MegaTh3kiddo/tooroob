/* پل بک‌اند ترب (FastAPI): استعلام واقعی از فروشنده (اپ اندروید فروشنده) و دستیار هوشمند روی کاتالوگ واقعی.
   همهٔ درخواست‌ها به /api/v1 می‌روند که Next.js آن را به سرور بک‌اند پراکسی می‌کند.
   فروشگاه‌های دادهٔ نمونه (s1، s2، …) به فروشگاه دموی متصل به اپ فروشنده نگاشت می‌شوند؛
   فروشگاه‌های واقعی کاتالوگ (shop_…) مستقیم استعلام می‌گیرند. */
(function (NQ) {
  'use strict';
  var BASE = '/api/v1';
  var DEMO_MERCHANT_SHOP = 'shop_jimbo_test';   // «فروشگاه جیمبو» — فروشندهٔ تست: ۰۹۱۲۰۰۰۰۰۰۰ (کد ۱۲۳۴۵۶)
  var CUSTOMER = 'cust_demo_01';
  var online = null;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function merchantShop(sid) {
    if (/^shop_/.test(sid)) return sid;
    return lsGet('nq-merchant-shop') || DEMO_MERCHANT_SHOP;
  }
  function req(path, opt) {
    opt = opt || {};
    return fetch(BASE + path, {
      method: opt.method || 'GET',
      headers: { 'Content-Type': 'application/json', 'X-User-Role': 'customer', 'X-User-ID': CUSTOMER },
      body: opt.body ? JSON.stringify(opt.body) : undefined
    }).then(function (r) {
      if (!r.ok) {
        if (r.status >= 500) online = false;
        throw new Error(r.status);
      }
      online = true;
      return r.json();
    }).catch(function (err) {
      if (typeof navigator !== 'undefined' && !navigator.onLine) online = false;
      throw err;
    });
  }
  function esc(t) { return String(t == null ? '' : t).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fa(n) { return Math.round(n).toLocaleString('fa-IR'); }
  function pct(x) { return fa((x || 0) * 100) + '٪'; }

  /* ---------- استعلام ---------- */
  function sendInquiry(q, info) {
    var catName = q.cat && NQ.CATS ? ((NQ.CATS.filter(function (c) { return c.id === q.cat; })[0]) || {}).name : '';
    return req('/customer/inquiries', {
      method: 'POST',
      body: {
        shop_id: merchantShop(q.sid),
        product_title: q.title || catName || 'کالای درخواستی',
        recorded_price_toman: Math.round(info.price || 0),
        customer_name: 'کاربر ترب مپ',
        user_note: info.shopName ? 'استعلام از طریق ترب مپ برای «' + info.shopName + '»' : null
      }
    }).then(function (d) {
      q.remote = d.inquiry_id; q.track = d.tracking_code; NQ.Inq.save(); poll();
      return true;
    }).catch(function () { online = false; return false; });
  }

  var polling = false;
  function poll() {
    if (polling || !NQ.Inq) return;
    var open = NQ.Inq.list().filter(function (q) { return q.remote && q.status === 'pending'; });
    if (!open.length) return;
    polling = true;
    req('/customer/inquiries?customer_id=' + CUSTOMER).then(function (rows) {
      var byId = {}; rows.forEach(function (r) { byId[r.inquiry_id] = r; });
      open.forEach(function (q) {
        var r = byId[q.remote]; if (!r) return;
        var st = String(r.status).toUpperCase();
        if (st === 'ANSWERED' || st === 'OUT_OF_STOCK') {
          var inStock = st === 'ANSWERED' && r.is_in_stock !== false;
          NQ.Inq.applyRemote(q, {
            status: 'answered',
            answer: { price: r.offered_price_toman || r.recorded_price_toman || 0, stock: inStock ? 'in' : 'out', note: r.response_notes || (inStock ? 'موجود است.' : 'فعلاً موجود نیست.'), at: Date.now() }
          });
        } else if (st === 'EXPIRED' || st === 'DECLINED') {
          NQ.Inq.applyRemote(q, { status: 'noreply' });
        }
      });
    }).catch(function () {}).then(function () { polling = false; });
  }
  setInterval(poll, 4000);
  setTimeout(poll, 800);

  /* ---------- دستیار هوشمند ---------- */
  var SESSION_KEY = 'nq-bk-session';
  function session() {
    var s = null; try { s = sessionStorage.getItem(SESSION_KEY); } catch (e) {}
    if (s) return Promise.resolve(s);
    return req('/assistant/sessions', { method: 'POST', body: { customer_id: CUSTOMER } }).then(function (d) {
      try { sessionStorage.setItem(SESSION_KEY, d.session_id); } catch (e) {}
      return d.session_id;
    });
  }
  function send(sid, text) {
    var origin = (NQ.state && NQ.state.origin) || (NQ.getOrigin && NQ.getOrigin()) || NQ.ORIGIN || { lat: 35.70450, lng: 51.39447 };
    return req('/assistant/sessions/' + sid + '/messages', {
      method: 'POST',
      body: {
        message: text,
        user_lat: origin.lat,
        user_lon: origin.lng || origin.lon
      }
    });
  }
  function mdLite(t) {
    if (!t) return '';
    var safe = esc(t);
    safe = safe.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
    safe = safe.replace(/^[\s]*[•\*\-]\s+(.+)$/gm, '<div class="ag-bullet">• $1</div>');
    safe = safe.replace(/^[\s]*(\d+)[.)]\s+(.+)$/gm, '<div class="ag-bullet"><b>$1.</b> $2</div>');
    safe = safe.replace(/\n{2,}/g, '<br><br>').replace(/\n/g, '<br>');
    return safe;
  }
  var LABELS = { best_overall: 'بهترین انتخاب', budget_pick: 'اقتصادی‌ترین', verified_confidence: 'مطمئن‌ترین فروشگاه', closest: 'نزدیک‌ترین', fastest: 'سریع‌ترین' };
  var shown = {};
  function ensureShop(rec) {
    if (!NQ.STORES) NQ.STORES = {};
    if (!NQ.STORES[rec.shop_id]) {
      NQ.STORES[rec.shop_id] = {
        name: rec.shop_name,
        addr: rec.shop_address || 'تهران',
        lat: rec.shop_lat || (NQ.CENTER ? NQ.CENTER.lat : 35.70450),
        lng: rec.shop_lon || (NQ.CENTER ? NQ.CENTER.lng : 51.39447),
        hours: rec.shop_hours_desc || '۹ تا ۲۱',
        openH: 9,
        closeH: 21,
        phone: '',
        phones: [],
        installments: [],
        rating: null,
        real: true
      };
      req('/shops/' + rec.shop_id).then(function (s) {
        var st = NQ.STORES[rec.shop_id];
        if (st) {
          if (s.latitude || s.lat) { st.lat = +(s.latitude || s.lat); st.lng = +(s.longitude || s.lon || s.lng); }
          if (s.phone) st.phone = s.phone;
          if (s.address) st.addr = s.address;
        }
      }).catch(function () {});
    } else {
      if (rec.shop_lat && rec.shop_lon) {
        NQ.STORES[rec.shop_id].lat = rec.shop_lat;
        NQ.STORES[rec.shop_id].lng = rec.shop_lon;
      }
    }
  }

  function cardHTML(rec, i) {
    var key = 'bk' + Date.now() + '_' + i; shown[key] = rec;
    ensureShop(rec);
    var lbl = LABELS[rec.trade_off_label] || 'پیشنهاد ترب';
    var isBest = rec.trade_off_label === 'best_overall' || rec.trade_off_label === 'budget_pick';
    var isClosest = rec.trade_off_label === 'closest';
    var badgeTag = '<span class="tag ' + (isBest ? 'best' : isClosest ? 'near' : 'near') + '">' + lbl + '</span>';

    // Store art/icon
    var art = (NQ.StoreInfo && NQ.StoreInfo(rec.shop_id) && NQ.StoreInfo(rec.shop_id).art) ||
      '<svg class="ic" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>';

    // Stock tag
    var stockCls = (rec.stock_survival_at_arrival === null || rec.stock_survival_at_arrival >= 0.7) ? 'in' : 'unsure';
    var stockTxt = stockCls === 'in' ? 'موجود' : 'نیازمند استعلام';
    var stockTag = '<span class="stock ' + stockCls + '">' + stockTxt + '</span>';

    // Open/Closed badge
    var isOpen = rec.is_shop_open !== false;
    var openTag = isOpen
      ? '<span class="tag open">باز است</span>'
      : '<span class="tag" style="background:var(--elevated);color:var(--muted);border:1px solid var(--line);">ساعات کاری ثبت‌شده</span>';

    // Distance tag
    var distTag = (rec.distance_km != null)
      ? '<span class="tag" style="background:var(--elevated);color:var(--text);border:1px solid var(--line);">📍 ' + fa(rec.distance_km) + ' کیلومتر</span>'
      : '';

    // Product-side highlight (specs, battery, audio quality, etc.)
    var feat = '';
    if (rec.pros && rec.pros.length) {
      for (var p = 0; p < rec.pros.length; p++) {
        var proText = rec.pros[p];
        if (proText.indexOf('فروشگاه') === -1) {
          feat = proText;
          break;
        }
      }
      if (!feat) feat = rec.pros[0];
    }

    var refHtml = rec.reference_market_price ? '<small class="bk-ref"> (میانه: ' + fa(rec.reference_market_price) + ')</small>' : '';

    return '<article class="ag-card" data-sid="' + esc(rec.shop_id) + '">' +
      '<div class="ag-c-top" style="cursor:pointer" data-bk-cardview="' + key + '">' +
        '<span class="ag-c-art" aria-hidden="true">' + art + '</span>' +
        '<b class="ag-c-name" title="' + esc(rec.shop_name) + '">' + esc(rec.shop_name) + '</b>' +
        stockTag +
      '</div>' +
      '<p class="ag-c-prod" title="' + esc(rec.product_title) + '" style="cursor:pointer" data-bk-cardview="' + key + '">' + esc(rec.product_title) + '</p>' +
      (feat ? '<p class="ag-c-feat">✨ ' + esc(feat) + '</p>' : '') +
      '<p class="ag-c-price"><b>' + fa(rec.price_toman) + '</b> <small>تومان</small>' + refHtml + '</p>' +
      '<p class="ag-c-meta">' +
        badgeTag +
        distTag +
        openTag +
        (rec.shop_address ? '<span class="ag-c-addr" title="' + esc(rec.shop_address) + '">' + esc(rec.shop_address) + '</span>' : '') +
      '</p>' +
      '<div class="ag-c-acts">' +
        '<button type="button" class="ag-pick" data-bk-view="' + key + '" title="مشاهدهٔ جزئیات فروشگاه و کالا">' +
          '<svg class="ic" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/></svg>' +
          '<span>مشاهده</span>' +
        '</button>' +
        '<button type="button" class="ag-go" data-bk-smap="' + key + '" title="روی نقشه" aria-label="روی نقشه">' +
          '<svg class="ic" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/></svg>' +
          '<span>روی نقشه</span>' +
        '</button>' +
      '</div>' +
    '</article>';
  }
  /* مقایسه: بهترین پیشنهاد هر کالا کنار هم (فقط داده‌های واقعی کاتالوگ) */
  function compareHTML(recs) {
    var by = {}, order = [];
    recs.forEach(function (r) {
      if (!by[r.product_id]) { by[r.product_id] = { title: r.product_title, min: r.price_toman, ref: r.reference_market_price, trust: r.shop_reliability_score, stock: r.stock_survival_at_arrival, n: 0 }; order.push(r.product_id); }
      var b = by[r.product_id]; b.n++;
      if (r.price_toman < b.min) { b.min = r.price_toman; b.trust = r.shop_reliability_score; b.stock = r.stock_survival_at_arrival; }
    });
    var cols = order.slice(0, 3).map(function (id) { return by[id]; });
    if (cols.length < 2) return '<p class="ag-t">برای مقایسه فقط یک کالا در کاتالوگ پیدا شد؛ پیشنهادهایش:</p>';
    var cheapest = cols.reduce(function (a, b) { return b.min < a.min ? b : a; });
    function row(label, fn) { return '<tr><th>' + label + '</th>' + cols.map(function (c) { return '<td>' + fn(c) + '</td>'; }).join('') + '</tr>'; }
    return '<p class="ag-t">مقایسهٔ کالاها بر اساس پیشنهادهای واقعی فروشگاه‌ها:</p>' +
      '<div class="bk-cmp"><table><thead><tr><th></th>' + cols.map(function (c) { return '<th>' + esc(c.title) + '</th>'; }).join('') + '</tr></thead><tbody>' +
      row('کمترین قیمت', function (c) { return '<b' + (c === cheapest ? ' class="bk-best"' : '') + '>' + fa(c.min) + '</b> <small>تومان</small>'; }) +
      row('میانهٔ بازار', function (c) { return c.ref ? fa(c.ref) : '—'; }) +
      row('اعتماد فروشگاه', function (c) { return pct(c.trust); }) +
      row('احتمال موجودی', function (c) { return pct(c.stock); }) +
      '</tbody></table></div>';
  }

  function chat(text) {
    return session().then(function (sid) {
      return send(sid, text).catch(function (e) {
        try { sessionStorage.removeItem(SESSION_KEY); } catch (x) {}
        return session().then(function (s2) { return send(s2, text); });
      });
    }).then(function (d) {
      var recs = ((d.recommendations || {}).top_recommendations || []).slice(0, 6);
      var h = '';
      NQ.Backend.awaitingAnswer = !!(d.active_clarification && d.active_clarification.question);
      if (NQ.Backend.awaitingAnswer) recs = [];

      // If active clarification is present, strip bullet options from reply_text so options aren't shown twice
      if (d.active_clarification && (d.active_clarification.options || []).length && d.reply_text) {
        d.reply_text = d.reply_text.replace(/(\n\s*•[^\n]+)+$/g, '').trim();
      }

      // Primary conversational response from assistant
      if (d.reply_text) {
        h += '<p class="ag-t ag-chat-msg">' + mdLite(d.reply_text) + '</p>';
      }

      // Comparison table if comparing products
      if (recs.length && d.detected_intent === 'product_comparison') {
        h += compareHTML(recs);
      }

      // Recommended product/store cards from real catalogue
      if (recs.length) {
        h += '<div class="ag-group"><div class="ag-cards bk-cards">' + recs.map(cardHTML).join('') + '</div></div>' +
          '<p class="bk-note">برای مشاهدهٔ جزئیات فروشگاه روی «مشاهده» یا «روی نقشه» بزنید.</p>';
      }

      // Clarification question options (chips)
      if (d.active_clarification && (d.active_clarification.options || []).length) {
        var c = d.active_clarification;
        if (!d.reply_text && c.question) {
          h = '<p class="ag-t ag-chat-msg">' + mdLite(c.question) + '</p>' + h;
        }
        h += '<div class="ag-chips">' + c.options.map(function (o) { return '<button type="button" class="ag-chip" data-ag-ask="' + esc(o) + '">' + esc(o) + '</button>'; }).join('') + '</div>';
      }

      return h || '<p class="ag-t">در حال بررسی پاسخ شما هستم...</p>';
    }).catch(function () { return null; });
  }

  /* تعامل با کارت‌های فروشگاه در گفتگو (مشاهده جزئیات / نقشه) */
  document.addEventListener('click', function (e) {
    var vBtn = e.target.closest && e.target.closest('[data-bk-view],[data-bk-cardview]');
    if (vBtn) {
      var key = vBtn.getAttribute('data-bk-view') || vBtn.getAttribute('data-bk-cardview');
      var rec = shown[key];
      if (!rec) return;
      ensureShop(rec);
      if (NQ.App && NQ.App.storeDialog) {
        NQ.App.storeDialog(rec.shop_id, null, rec.product_title);
      }
      return;
    }
    var mBtn = e.target.closest && e.target.closest('[data-bk-smap]');
    if (mBtn) {
      var rec2 = shown[mBtn.getAttribute('data-bk-smap')];
      if (!rec2) return;
      ensureShop(rec2);
      if (NQ.App && NQ.App.storeOnMap) {
        NQ.App.storeOnMap(rec2.shop_id);
      }
      return;
    }
  });

  NQ.Backend = { sendInquiry: sendInquiry, chat: chat, poll: poll, isOnline: function () { return online !== false; }, active: false, awaitingAnswer: false };
})(window.NQ = window.NQ || {});
