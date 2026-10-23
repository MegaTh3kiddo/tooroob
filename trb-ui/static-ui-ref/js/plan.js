/* برنامهٔ سر زدن — منطق ذخیرهٔ فروشگاه‌ها، اولویت‌بندی و زمان‌بندی (بدون وابستگی به DOM)
   هر «توقف» یک فروشگاه است که می‌تواند برای چند محصول/موضوع ذخیره شده باشد:
     { sid: 's1', cats: ['headphone','charger'], done: false }
   ترتیب آرایه همان اولویت سر زدن است. */
(function (NQ) {
  'use strict';

  var KEY = 'nq-plan-v1';
  var DWELL = 10;        // دقیقه توقف در هر فروشگاه
  var SOON = 60;         // «زود می‌بندد»: کمتر از ۶۰ دقیقه تا بسته شدن
  var MODES = ['near', 'closing', 'smart']; // هر چیز دیگر = دستی

  var plan = { stops: [], mode: 'smart', depart: null };

  /* ---------- ابزارها ---------- */
  function roadKm(a, b) { return NQ.geo.distanceKm(a, b) * 1.3; }
  /* زمان رفت‌وآمد طبق روش انتخابی کاربر (js/travel.js) */
  function travelMin(km, sid) { return NQ.Travel.minutesFor(km, sid); }
  function parseHM(s) {
    var m = /^(\d{1,2}):(\d{2})$/.exec(s || ''); if (!m) return null;
    return Math.min(23, +m[1]) * 60 + Math.min(59, +m[2]);
  }
  function nowMin() { var d = new Date(); return d.getHours() * 60 + d.getMinutes(); }
  function departMin() { var m = parseHM(plan.depart); return m == null ? nowMin() : m; }
  function find(sid) { for (var i = 0; i < plan.stops.length; i++) if (plan.stops[i].sid === sid) return plan.stops[i]; return null; }

  /* ---------- ذخیره‌سازی ---------- */
  function save() { try { localStorage.setItem(KEY, JSON.stringify(plan)); } catch (e) {} }
  function load() {
    try {
      var d = JSON.parse(localStorage.getItem(KEY) || 'null'); if (!d) return;
      plan.mode = d.mode || 'smart';
      plan.depart = parseHM(d.depart) == null ? null : d.depart;
      var catIds = NQ.CATS.map(function (c) { return c.id; });
      plan.stops = (d.stops || []).filter(function (s) { return NQ.STORES[s.sid]; }).map(function (s) {
        return { sid: s.sid, cats: (s.cats || []).filter(function (c) { return catIds.indexOf(c) > -1; }), done: !!s.done };
      }).filter(function (s) { return s.cats.length; });
    } catch (e) {}
  }

  /* ---------- ترتیب‌دهی ---------- */
  function sortNear(list, origin) {
    return list.slice().sort(function (a, b) {
      return roadKm(origin, NQ.STORES[a.sid]) - roadKm(origin, NQ.STORES[b.sid]);
    });
  }
  /* زودتر می‌بندد اول؛ فروشگاه‌هایی که تا زمان حرکت بسته شده‌اند آخر */
  function sortClosing(list, origin) {
    var t = departMin();
    return list.slice().sort(function (a, b) {
      var A = NQ.STORES[a.sid], B = NQ.STORES[b.sid];
      var ca = A.closeH * 60 <= t, cb = B.closeH * 60 <= t;
      return (ca - cb) || (A.closeH - B.closeH) || (roadKm(origin, A) - roadKm(origin, B));
    });
  }
  /* مسیر هوشمند: هر بار کاندیدای بعدی را از جایی که هستیم انتخاب می‌کند.
     اولویت: ۱) فروشگاهی که تا رسیدن هنوز باز است  ۲) اگر کمتر از ۶۰ دقیقه به بسته شدنش مانده، فوری‌تر اول
     ۳) در غیر این صورت نزدیک‌ترین (با کمی جریمه برای صبر کردن تا بازشدن). بسته‌ها آخر. */
  function sortSmart(list, origin) {
    var t = departMin(), pos = origin, rest = list.slice(), out = [];
    while (rest.length) {
      var best = null;
      rest.forEach(function (st) {
        var S = NQ.STORES[st.sid], km = roadKm(pos, S), arr = t + travelMin(km, st.sid);
        var open = S.openH * 60, close = S.closeH * 60;
        var c = { st: st, S: S, km: km, arr: arr, ok: arr < close, slack: close - arr, wait: Math.max(0, open - arr) };
        c.urgent = c.ok && c.slack <= SOON;
        if (!best || better(c, best)) best = c;
      });
      out.push(best.st);
      rest.splice(rest.indexOf(best.st), 1);
      if (best.ok) { t = Math.max(best.arr, best.S.openH * 60) + DWELL; pos = best.S; }
    }
    return out;
    function better(a, b) {
      if (a.ok !== b.ok) return a.ok;
      if (a.urgent !== b.urgent) return a.urgent;
      if (a.urgent && b.urgent) return a.slack < b.slack;
      return (a.km + a.wait * 0.1) < (b.km + b.wait * 0.1);
    }
  }
  var SORTERS = { near: sortNear, closing: sortClosing, smart: sortSmart };

  /* توقف‌های انجام‌شده همیشه آخر لیست می‌مانند */
  function applyMode(origin) {
    if (MODES.indexOf(plan.mode) < 0) return false;
    var active = plan.stops.filter(function (s) { return !s.done; });
    var done = plan.stops.filter(function (s) { return s.done; });
    var next = SORTERS[plan.mode](active, origin).concat(done);
    var changed = next.some(function (s, i) { return s !== plan.stops[i]; });
    if (changed) { plan.stops = next; save(); }
    return changed;
  }

  /* ---------- زمان‌بندی ----------
     برای هر توقف: فاصله از توقف قبلی، زمان رسیدن، و وضعیت باز/بسته بودن هنگام رسیدن
       open  = باز و بیش از ۶۰ دقیقه تا بسته شدن
       soon  = باز ولی کمتر از ۶۰ دقیقه مانده
       later = هنگام رسیدن هنوز باز نشده (صبر می‌کنیم تا باز شود)
       closed= هنگام رسیدن بسته است */
  function schedule(origin) {
    var start = departMin(), t = start, pos = origin, totalKm = 0, n = 0, warnings = 0, rows = [];
    plan.stops.forEach(function (st) {
      var S = NQ.STORES[st.sid], row = { st: st, S: S };
      rows.push(row);
      if (st.done) { row.done = true; return; }
      var km = roadKm(pos, S), tm = travelMin(km, st.sid), arr = t + tm;
      var open = S.openH * 60, close = S.closeH * 60;
      row.n = ++n; row.km = km; row.tm = tm; row.mode = NQ.Travel.resolve(km, st.sid); row.arrive = arr; row.openM = open; row.closeM = close; row.left = close - arr;
      row.status = arr >= close ? 'closed' : arr < open ? 'later' : (close - arr <= SOON ? 'soon' : 'open');
      if (row.status === 'closed' || row.status === 'later') warnings++;
      totalKm += km;
      t = row.status === 'closed' ? arr : Math.max(arr, open) + DWELL;
      pos = S;
    });
    return { rows: rows, start: start, end: t, totalKm: totalKm, totalMin: t - start, active: n, warnings: warnings };
  }

  NQ.Plan = {
    DWELL: DWELL,
    get stops() { return plan.stops; },
    get mode() { return plan.mode; },
    get depart() { return plan.depart; },
    load: load,
    count: function () { return plan.stops.length; },
    has: function (sid, cat) { var s = find(sid); return !!s && s.cats.indexOf(cat) > -1; },
    hasStore: function (sid) { return !!find(sid); },
    /* ذخیره / برداشتن یک فروشگاه برای یک موضوع؛ true یعنی ذخیره شد */
    toggle: function (sid, cat) {
      var s = find(sid), saved = true;
      if (!s) plan.stops.push({ sid: sid, cats: [cat], done: false });
      else {
        var i = s.cats.indexOf(cat);
        if (i > -1) { s.cats.splice(i, 1); saved = false; if (!s.cats.length) plan.stops.splice(plan.stops.indexOf(s), 1); }
        else s.cats.push(cat);
      }
      save(); return saved;
    },
    removeCat: function (sid, cat) { if (NQ.Plan.has(sid, cat)) NQ.Plan.toggle(sid, cat); },
    remove: function (sid) { var s = find(sid); if (s) { plan.stops.splice(plan.stops.indexOf(s), 1); save(); } },
    clear: function () { plan.stops = []; save(); },
    setDone: function (sid, v) {
      var s = find(sid); if (!s) return;
      s.done = !!v;
      /* انجام‌شده‌ها ته لیست، برگشته‌ها به انتهای فعال‌ها */
      plan.stops.splice(plan.stops.indexOf(s), 1);
      if (s.done) plan.stops.push(s);
      else { var firstDone = plan.stops.findIndex(function (x) { return x.done; }); plan.stops.splice(firstDone < 0 ? plan.stops.length : firstDone, 0, s); }
      save();
    },
    /* جابه‌جایی دستی (dir: -1 بالا، +1 پایین) و رفتن به حالت «دستی» */
    move: function (sid, dir) {
      var s = find(sid); if (!s) return false;
      var i = plan.stops.indexOf(s), j = i + dir;
      if (j < 0 || j >= plan.stops.length || plan.stops[j].done !== s.done) return false;
      plan.stops[i] = plan.stops[j]; plan.stops[j] = s;
      plan.mode = 'manual'; save(); return true;
    },
    setMode: function (m, origin) { plan.mode = m; applyMode(origin); save(); },
    setDepart: function (hm) { plan.depart = parseHM(hm) == null ? null : hm; save(); },
    applyMode: applyMode,
    schedule: schedule,
    parseHM: parseHM
  };
})(window.NQ = window.NQ || {});
