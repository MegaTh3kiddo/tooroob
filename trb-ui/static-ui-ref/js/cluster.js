/* خوشه‌بندی پین‌ها بر اساس «برخورد روی صفحه» (بدون وابستگی به DOM یا Leaflet)

   الگوریتم: تجمیعیِ سلسله‌مراتبی (agglomerative) در فضای پیکسلِ همان زوم.
   ۱) فقط پین‌هایی با group یکسان (مثلاً یک محصول مشترک) اجازهٔ ادغام دارند؛ پین‌های fixed (انتخاب‌شده و ...) مستقل می‌مانند.
   ۲) فاصلهٔ دو خوشه = max(|dx|/W, |dy|/H) یعنی نسبت به اندازهٔ واقعی پین؛ زیر ۱ = روی هم افتاده‌اند.
      هرچه بیشتر زوم‌اوت کنیم، همان فاصلهٔ واقعی پیکسل کمتر می‌شود و خوشه‌ها بزرگ‌تر می‌شوند.
      زیر زوم relaxBelow، W و H کمی بزرگ می‌شوند تا در زوم‌اوتِ زیاد نقشه شلوغ نشود.
   ۳) در هر مرحله نزدیک‌ترین جفت ادغام می‌شود و مرکز جدید «میانگین وزنی» اعضا (به تعداد) است؛ تا وقتی هیچ جفتی برخورد نداشته باشد.
   ۴) از زوم offZoom به بعد هیچ ادغامی انجام نمی‌شود: همه مستقل‌اند. */
(function (NQ) {
  'use strict';

  var DEFAULTS = { W: 78, H: 34, offZoom: 16, relaxBelow: 13, relaxStep: 0.15 };

  /* points: [{id, lat, lng, group, fixed}]
     opts: {zoom, project(lat,lng)->{x,y}, W, H, offZoom, relaxBelow, relaxStep}
     خروجی: [{members:[point...], lat, lng, count}] — lat/lng = میانگین وزنیِ موقعیت اعضا */
  function build(points, opts) {
    var o = {}; for (var k in DEFAULTS) o[k] = (opts && opts[k] != null) ? opts[k] : DEFAULTS[k];
    var zoom = opts.zoom, project = opts.project;
    var pts = points.slice().sort(function (a, b) { return a.id < b.id ? -1 : a.id > b.id ? 1 : 0; });
    var out = [];

    function single(p) { return { members: [p], lat: p.lat, lng: p.lng, count: 1 }; }
    if (zoom >= o.offZoom) return pts.map(single);

    var relax = zoom >= o.relaxBelow ? 1 : 1 + (o.relaxBelow - zoom) * o.relaxStep;
    var W = o.W * relax, H = o.H * relax;

    var groups = {}, order = [];
    pts.forEach(function (p) {
      if (p.fixed || p.group == null) { out.push(single(p)); return; }
      var g = String(p.group);
      if (!groups[g]) { groups[g] = []; order.push(g); }
      groups[g].push(p);
    });

    order.forEach(function (g) {
      var cl = groups[g].map(function (p) {
        var xy = project(p.lat, p.lng);
        return { members: [p], x: xy.x, y: xy.y, lat: p.lat, lng: p.lng, n: 1 };
      });
      for (;;) {
        var bi = -1, bj = -1, best = 1;
        for (var i = 0; i < cl.length; i++) {
          for (var j = i + 1; j < cl.length; j++) {
            var d = Math.max(Math.abs(cl[i].x - cl[j].x) / W, Math.abs(cl[i].y - cl[j].y) / H);
            if (d < best) { best = d; bi = i; bj = j; }
          }
        }
        if (bi < 0) break;
        var a = cl[bi], b = cl[bj], n = a.n + b.n;
        cl[bi] = {
          members: a.members.concat(b.members), n: n,
          x: (a.x * a.n + b.x * b.n) / n, y: (a.y * a.n + b.y * b.n) / n,
          lat: (a.lat * a.n + b.lat * b.n) / n, lng: (a.lng * a.n + b.lng * b.n) / n
        };
        cl.splice(bj, 1);
      }
      cl.forEach(function (c) {
        out.push(c.n === 1 ? single(c.members[0]) : { members: c.members, lat: c.lat, lng: c.lng, count: c.n });
      });
    });
    return out;
  }

  NQ.Cluster = { build: build, DEFAULTS: DEFAULTS };
})(window.NQ = window.NQ || {});
