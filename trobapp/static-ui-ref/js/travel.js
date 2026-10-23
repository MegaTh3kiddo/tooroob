/* روش رفت‌وآمد: پیاده، مترو/اتوبوس، ماشین، موتور یا «پیشنهادی» (خودکار)
   زمان = base + km × perKm (دقیقه). base همان زمان ثابت (انتظار ایستگاه، پارک و ...) است.
   اعداد تقریبی‌اند؛ برای دقت واقعی می‌شود با یک سرویس مسیریابی جایگزین کرد. */
(function (NQ) {
  'use strict';
  var KEY = 'nq-travel-v1';
  var DEF = {
    walk:    { label: 'پیاده',        base: 0,  perKm: 12,  maxKm: 3 },
    transit: { label: 'اتوبوس یا مترو',  base: 14, perKm: 1.9, maxKm: Infinity },
    car:     { label: 'ماشین',        base: 4,  perKm: 2.7, maxKm: Infinity },
    moto:    { label: 'موتور',        base: 3,  perKm: 2.2, maxKm: Infinity }
  };
  var ORDER = ['walk', 'transit', 'car'];   // اولویت در پیشنهاد: سبک‌تر/ارزان‌تر اول (موتور فقط انتخاب دستی است)
  var MENU = ['auto', 'car', 'moto', 'walk', 'transit']; // ترتیب نمایش در منو و کارت‌ها
  var mode = 'auto';
  try { var m = localStorage.getItem(KEY); if (m === 'auto' || DEF[m]) mode = m; } catch (e) {}

  /* روش مخصوص هر فروشگاه (مثلاً یکی را پیاده و دیگری را با موتور می‌روم) */
  var KEY2 = 'nq-travel-store-v1', per = {};
  try {
    var d = JSON.parse(localStorage.getItem(KEY2) || '{}');
    Object.keys(d).forEach(function (k) { if (DEF[d[k]]) per[k] = d[k]; });
  } catch (e) {}

  function minutes(id, km) { var d = DEF[id]; return Math.max(1, Math.round(d.base + km * d.perKm)); }

  /* پیشنهاد: از بین روش‌های منطقی برای این فاصله، سریع‌ترین را پیدا می‌کند؛ بعد سبک‌ترین روشی را
     که حداکثر max(۴ دقیقه، ۲۵٪) از سریع‌ترین کندتر است برمی‌گزیند (پیاده > مترو > ماشین). */
  function suggest(km) {
    var cand = ORDER.filter(function (id) { return km <= DEF[id].maxKm; });
    var fast = Math.min.apply(null, cand.map(function (id) { return minutes(id, km); }));
    var tol = Math.max(4, fast * 0.25);
    for (var i = 0; i < cand.length; i++) if (minutes(cand[i], km) <= fast + tol) return cand[i];
    return 'car';
  }
  function reason(id) {
    return { walk: 'فاصله کم است و پیاده‌روی ساده‌تر است',
             transit: 'بدون درگیری با ترافیک و پارک', car: 'فاصله زیاد است و ماشین سریع‌تر می‌رسد' }[id];
  }
  function resolve(km, sid) {
    if (sid && per[sid]) return per[sid];
    return mode === 'auto' ? suggest(km) : mode;
  }

  NQ.Travel = {
    ORDER: ORDER, MENU: MENU,
    label: function (id) { return id === 'auto' ? 'پیشنهادی' : DEF[id].label; },
    get mode() { return mode; },
    set: function (id) {
      if (id !== 'auto' && !DEF[id]) return;
      mode = id; try { localStorage.setItem(KEY, id); } catch (e) {}
    },
    minutes: minutes,
    suggest: suggest,
    reason: reason,
    resolve: resolve,
    /* زمان با روش انتخاب‌شده (در حالت پیشنهادی: بهترین روش برای همین فاصله) */
    minutesFor: function (km, sid) { return minutes(resolve(km, sid), km); },
    /* روش مخصوص یک فروشگاه؛ null یعنی از روش کلی پیروی می‌کند */
    modeFor: function (sid) { return per[sid] || null; },
    setFor: function (sid, id) {
      if (id && DEF[id]) per[sid] = id; else delete per[sid];
      try { localStorage.setItem(KEY2, JSON.stringify(per)); } catch (e) {}
    },
    all: function (km) { return MENU.slice(1).map(function (id) { return { id: id, min: minutes(id, km) }; }); }
  };
})(window.NQ = window.NQ || {});
