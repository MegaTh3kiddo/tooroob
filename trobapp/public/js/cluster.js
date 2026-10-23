/* خوشه‌بندی پین‌ها بر اساس «برخورد روی صفحه» (بدون وابستگی به DOM یا Leaflet)

   الگوریتم: تجمیعیِ سلسله‌مراتبی (agglomerative) در فضای پیکسلِ همان زوم.
   ۱) فاصلهٔ دو پین/خوشه = max(|dx|/W, |dy|/H) یعنی نسبت به اندازهٔ واقعی پین؛ زیر ۱ = روی هم افتاده‌اند.
   ۲) پین‌هایی که فاصلهٔ نزدیک دارند یا روی صفحه برخورد دارند در تمام زوم‌ها به عنوان یک آیتم ادغام می‌شوند
      تا از روی هم افتادن پین‌ها و اشکالات بصری جلوگیری شود.
   ۳) در هر مرحله نزدیک‌ترین جفتِ دارای برخورد ادغام می‌شود و مرکز جدید میانگین وزنیِ موقعیت اعضاست. */
(function (NQ) {
  'use strict';

  var DEFAULTS = { W: 78, H: 34, relaxBelow: 13, relaxStep: 0.15 };

  /* points: [{id, lat, lng, group, fixed}]
     opts: {zoom, project(lat,lng)->{x,y}, W, H, relaxBelow, relaxStep}
     خروجی: [{members:[point...], lat, lng, count, hasFixed}] */
  function build(points, opts) {
    opts = opts || {};
    var W = (opts.W != null ? opts.W : DEFAULTS.W);
    var H = (opts.H != null ? opts.H : DEFAULTS.H);
    var zoom = opts.zoom;
    var project = opts.project;
    var pts = points.slice().sort(function (a, b) { return a.id < b.id ? -1 : a.id > b.id ? 1 : 0; });
    if (!pts.length) return [];

    var relax = (opts.relaxBelow && zoom < opts.relaxBelow)
      ? 1 + (opts.relaxBelow - zoom) * (opts.relaxStep || 0.15)
      : 1;
    var effW = W * relax;
    var effH = H * relax;

    function single(p) { return { members: [p], lat: p.lat, lng: p.lng, count: 1, hasFixed: !!p.fixed }; }

    var cl = pts.map(function (p) {
      var xy = project(p.lat, p.lng);
      return {
        members: [p],
        x: xy.x,
        y: xy.y,
        lat: p.lat,
        lng: p.lng,
        n: 1,
        hasFixed: !!p.fixed
      };
    });

    for (;;) {
      var bi = -1, bj = -1, best = 1;
      for (var i = 0; i < cl.length; i++) {
        for (var j = i + 1; j < cl.length; j++) {
          var dx = Math.abs(cl[i].x - cl[j].x);
          var dy = Math.abs(cl[i].y - cl[j].y);
          var d = Math.max(dx / effW, dy / effH);
          if (d < best) {
            best = d;
            bi = i;
            bj = j;
          }
        }
      }
      if (bi < 0) break;
      var a = cl[bi], b = cl[bj], n = a.n + b.n;
      cl[bi] = {
        members: a.members.concat(b.members),
        n: n,
        x: (a.x * a.n + b.x * b.n) / n,
        y: (a.y * a.n + b.y * b.n) / n,
        lat: (a.lat * a.n + b.lat * b.n) / n,
        lng: (a.lng * a.n + b.lng * b.n) / n,
        hasFixed: a.hasFixed || b.hasFixed
      };
      cl.splice(bj, 1);
    }

    return cl.map(function (c) {
      return c.n === 1
        ? single(c.members[0])
        : { members: c.members, lat: c.lat, lng: c.lng, count: c.n, hasFixed: c.hasFixed };
    });
  }

  NQ.Cluster = { build: build, DEFAULTS: DEFAULTS };
})(window.NQ = window.NQ || {});
