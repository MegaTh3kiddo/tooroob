/* لایهٔ نقشه — تنها فایلی که مستقیم با Leaflet کار می‌کند.
   app.js فقط از NQ.MapView و NQ.geo استفاده می‌کند، پس اگر روزی بخواهید Leaflet را با MapLibre یا
   نقشهٔ دیگری عوض کنید، فقط همین فایل باید بازنویسی شود. */
(function (NQ) {
  'use strict';

  var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- ابزار جغرافیایی ---------- */
  var R = 6371; // شعاع زمین (کیلومتر)
  var rad = function (d) { return d * Math.PI / 180; };
  NQ.geo = {
    /* فاصلهٔ هوایی (کیلومتر) */
    distanceKm: function (a, b) {
      var dLat = rad(b.lat - a.lat), dLng = rad(b.lng - a.lng);
      var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
      return 2 * R * Math.asin(Math.sqrt(h));
    },
    mid: function (a, b) { return { lat: (a.lat + b.lat) / 2, lng: (a.lng + b.lng) / 2 }; }
  };

  /* ---------- نقشه ---------- */
  var map, pinsLayer, routesLayer, areaLayer = null, youMarker, handlers = {}, pins = {}, pendingFit = null;
  var items0 = [], spec0 = null, clusterOn = true, freshNext = false, insets = { t: 0, b: 0, r: 0 }, circleLayer = null, circleKey = '';

  function pinIcon(p, fresh) {
    return L.divIcon({
      className: 'pin ' + p.cls + (fresh ? ' fresh' : ''),
      html: '<span class="pw">' + p.html + '</span>',
      iconSize: [0, 0], iconAnchor: [0, 0]
    });
  }
  function decorate(marker, label) {
    var el = marker.getElement();
    if (el) { el.setAttribute('aria-label', label); el.setAttribute('role', 'button'); }
  }

  /* ---- رسم پین‌ها و خوشه‌ها ---- */
  function zoomToCluster(c) {
    var b = L.latLngBounds(c.members.map(function (m) { return [m.lat, m.lng]; }));
    var size = map.getSize(), cur = map.getZoom();
    var spanKm = NQ.geo.distanceKm(b.getNorthEast(), b.getSouthWest());
    if (spanKm <= 0.04 || cur >= 16) {
      if (handlers.onSuperCloseClusterClick && handlers.onSuperCloseClusterClick(c)) return;
    }
    var z = map.getBoundsZoom(b, false, L.point(Math.min(120, size.x * .24), Math.min(170, size.y * .4)));
    z = Math.min(map.getMaxZoom(), Math.max(z, cur + 1));   // حداقل یک پله نزدیک‌تر، تا خوشه حتماً باز شود
    map.setView(b.getCenter(), z, { animate: !reduced });
  }
  function drawPins() {
    if (!map) return;
    var focused = null, ae = document.activeElement;
    Object.keys(pins).forEach(function (k) { if (pins[k].marker.getElement() === ae) focused = k; });

    var list = items0;
    if (clusterOn && spec0 && spec0.cluster && NQ.Cluster) {
      var z = map.getZoom();
      var res = NQ.Cluster.build(items0.map(function (i) {
        return { id: i.sid, lat: i.lat, lng: i.lng, group: i.group, fixed: i.fixed, ref: i };
      }), { zoom: z, project: function (lat, lng) { var q = map.project([lat, lng], z); return { x: q.x, y: q.y }; } });
      list = res.map(function (c) {
        if (c.count === 1) return c.members[0].ref;
        var refs = c.members.map(function (m) { return m.ref; }), v = spec0.cluster(refs);
        var anyFixed = c.hasFixed || refs.some(function (r) { return r && (r.fixed || (r.cls && r.cls.indexOf('sel') > -1)); });
        var isSel = anyFixed || (v.cls && v.cls.indexOf('sel') > -1);
        var clsStr = 'cluster ' + (v.cls || '') + (isSel && (v.cls || '').indexOf('sel') === -1 ? ' sel' : '');
        return { sid: 'c:' + c.members.map(function (m) { return m.id; }).join(','), lat: c.lat, lng: c.lng,
                 cls: clsStr.trim(), html: v.html, label: v.label,
                 z: isSel ? 4000 : 600, cluster: c };
      });
    }

    var keep = {};
    list.forEach(function (p) {
      var key = p.sid; keep[key] = true;
      var sig = p.cls + '|' + p.html, cur = pins[key];
      if (!cur) {
        var m = L.marker([p.lat, p.lng], { icon: pinIcon(p, freshNext), keyboard: true, zIndexOffset: p.z });
        (function (key, p) {
          m.on('click', function (e) {
            if (e.originalEvent) L.DomEvent.stopPropagation(e.originalEvent);
            if (p.cluster) zoomToCluster(p.cluster); else if (handlers.onPinClick) handlers.onPinClick(p.sid);
          });
        })(key, p);
        m.addTo(pinsLayer);
        decorate(m, p.label);
        pins[key] = { marker: m, sig: sig };
      } else {
        if (cur.sig !== sig) { cur.marker.setIcon(pinIcon(p, false)); decorate(cur.marker, p.label); cur.sig = sig; }
        cur.marker.setLatLng([p.lat, p.lng]);
        cur.marker.setZIndexOffset(p.z);
      }
    });
    Object.keys(pins).forEach(function (k) {
      if (!keep[k]) { pinsLayer.removeLayer(pins[k].marker); delete pins[k]; }
    });
    if (focused && pins[focused]) {
      var el = pins[focused].marker.getElement();
      if (el && el !== document.activeElement) el.focus({ preventScroll: true });
    }
    declutter();
  }

  /* برچسب‌هایی که روی هم افتاده‌اند (مثلاً چند فروشگاه در یک ساختمان) موقتاً بالاتر می‌روند تا جدا دیده شوند؛
     یک خط باریک برچسب را به نقطهٔ واقعی وصل می‌کند. مهم‌ترها (zIndex بیشتر، خوشه‌ها) سر جایشان می‌مانند.
     اندازه از offsetWidth خوانده می‌شود تا انیمیشن ظاهر شدن پین روی محاسبه اثر نگذارد. */
  function declutter() {
    var list = [], size = map.getSize(), minT = insets.t + 6, maxB = size.y - insets.b - 6;
    Object.keys(pins).forEach(function (k) {
      var m = pins[k].marker, el = m.getElement(), pw = el && el.querySelector('.pw');
      if (!pw) return;
      el.classList.remove('nudged', 'below'); el.style.removeProperty('--dy');
      var pt = map.latLngToContainerPoint(m.getLatLng()), w = pw.offsetWidth, h = pw.offsetHeight, cl = el.classList.contains('cluster');
      var t = cl ? pt.y - h / 2 : pt.y - 7 - h;
      list.push({ el: el, cl: cl, y: pt.y, h: h, z: (m.options.zIndexOffset || 0) + (cl ? 1e5 : 0), l: pt.x - w / 2, r: pt.x + w / 2, t: t });
    });
    list.sort(function (a, b) { return b.z - a.z; });
    var placed = [], g = 3;
    /* از top شروع می‌کند و تا وقتی با برچسب‌های قبلی برخورد دارد، در جهت dir (۱- بالا، ۱ پایین) جابه‌جا می‌شود */
    function slide(a, top, dir) {
      for (var guard = 0, hit = true; hit && guard < 5; guard++) {
        hit = false;
        for (var i = 0; i < placed.length; i++) {
          var p = placed[i];
          if (a.r > p.l + g && a.l < p.r - g && top + a.h > p.t + g && top < p.b - g) {
            top = dir < 0 ? Math.max(a.t - 45, p.t - 4 - a.h) : Math.min(a.t + 45, p.b + 4);
            hit = true;
          }
        }
      }
      return top;
    }
    list.forEach(function (a) {
      var top = a.cl ? a.t : slide(a, a.t, -1), below = false;
      /* بالا جا نیست (زیر نوار جستجو می‌رود) ← زیر نقطه قرار می‌گیرد */
      if (!a.cl && top !== a.t && top < minT) {
        var down = slide(a, a.y + 7, 1);
        if (down + a.h <= maxB) { top = down; below = true; }
      }
      if (below) { a.el.classList.add('nudged', 'below'); a.el.style.setProperty('--dy', (top - a.y) + 'px'); }
      else if (top !== a.t) { a.el.classList.add('nudged'); a.el.style.setProperty('--dy', (top - a.t) + 'px'); }
      placed.push({ l: a.l, r: a.r, t: top, b: top + a.h });
    });
  }

  NQ.MapView = {
    init: function (el, h) {
      handlers = h || {};
      map = L.map(el, {
        zoomControl: false, minZoom: 3, maxZoom: 19,
        zoomSnap: 0.5, wheelPxPerZoomLevel: 100
      }).setView([NQ.CENTER.lat, NQ.CENTER.lng], 13);

      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        /* OSM بدون Referer تایل نمی‌دهد؛ پس صفحه را با http://localhost باز کنید، نه file:// */
        referrerPolicy: 'strict-origin-when-cross-origin',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>'
      }).addTo(map);
      map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');

      routesLayer = L.layerGroup().addTo(map);
      pinsLayer = L.layerGroup().addTo(map);

      map.on('click', function () { if (handlers.onBackgroundClick) handlers.onBackgroundClick(); });
      /* جابه‌جایی نقشه (برای «جستجو در این محدوده») */
      map.on('moveend', function () { declutter(); if (handlers.onMoveEnd) handlers.onMoveEnd(); });
      /* شروع کشیدن نقشه با دست کاربر (نه حرکت برنامه‌ای) */
      map.on('dragstart', function () { if (handlers.onDragStart) handlers.onDragStart(); });
      /* با تغییر زوم، خوشه‌ها دوباره محاسبه می‌شوند */
      map.on('zoomend', function () { freshNext = !reduced; drawPins(); freshNext = false; });

      /* اندازهٔ نقشه (مثلاً با تغییر چیدمان موبایل/دسکتاپ) عوض می‌شود */
      if ('ResizeObserver' in window) {
        new ResizeObserver(function () {
          map.invalidateSize({ animate: false });
          if (pendingFit && map.getSize().x) { var f = pendingFit; pendingFit = null; NQ.MapView.fit(f); }
        }).observe(el);
      }
    },

    /* ---- نقطهٔ «شما» ---- */
    setOrigin: function (ll) {
      if (!youMarker) {
        youMarker = L.marker([ll.lat, ll.lng], {
          draggable: true, keyboard: true, zIndexOffset: 2000, autoPan: true,
          icon: L.divIcon({
            className: 'you', html: '<i></i><span class="tg">شما</span>',
            iconSize: [44, 44], iconAnchor: [22, 22]
          })
        }).addTo(map);
        var label = 'موقعیت شما. با کشیدن یا با کلیدهای جهت‌نما جابه‌جا می‌شود.';
        decorate(youMarker, label);
        youMarker.on('drag', function (e) {
          if (handlers.onOriginMove) handlers.onOriginMove({ lat: e.latlng.lat, lng: e.latlng.lng }, true);
        });
        youMarker.getElement().addEventListener('keydown', function (e) {
          var k = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
          if (!k) return;
          e.preventDefault(); e.stopPropagation(); // نگذار نقشه هم جابه‌جا شود
          var step = e.shiftKey ? 60 : 20;
          var pt = map.latLngToContainerPoint(youMarker.getLatLng());
          var ll2 = map.containerPointToLatLng(L.point(pt.x + k[0] * step, pt.y + k[1] * step));
          youMarker.setLatLng(ll2);
          if (handlers.onOriginMove) handlers.onOriginMove({ lat: ll2.lat, lng: ll2.lng }, false);
        });
        return;
      }
      var cur = youMarker.getLatLng();
      if (Math.abs(cur.lat - ll.lat) > 1e-9 || Math.abs(cur.lng - ll.lng) > 1e-9) youMarker.setLatLng([ll.lat, ll.lng]);
    },

    /* ---- پین‌های قیمت ----
       items: [{sid, lat, lng, cls, html, label, z, group?, fixed?}]
       spec (اختیاری): {cluster: function(items) -> {cls, html, label}} برای ساختن ظاهر خوشه.
       فقط پین‌های دارای group (مثلاً «یک محصول مشترک») ادغام می‌شوند؛ بقیه همیشه مستقل‌اند. */
    /* محدودهٔ فعلی نقشه {n,s,e,w} و کادر خط‌چینِ محدودهٔ جستجو */
    getBounds: function () {
      var b = map.getBounds();
      return { n: b.getNorth(), s: b.getSouth(), e: b.getEast(), w: b.getWest() };
    },
    setArea: function (a) {
      if (areaLayer) { map.removeLayer(areaLayer); areaLayer = null; }
      if (a) areaLayer = L.rectangle([[a.s, a.w], [a.n, a.e]], { className: 'area-box', weight: 2, dashArray: '6 6', fill: true, fillOpacity: .04, interactive: false }).addTo(map);
    },
    /* دایرهٔ منطقه (فروشگاه‌های یک محله، «اطراف من»، پرتراکم‌ترین محدوده): {lat, lng, r(کیلومتر)} یا null */
    setCircle: function (c) {
      var key = c ? c.lat + ',' + c.lng + ',' + c.r : '';
      if (key === circleKey) return;
      circleKey = key;
      if (circleLayer) { map.removeLayer(circleLayer); circleLayer = null; }
      if (c) circleLayer = L.circle([c.lat, c.lng], { radius: c.r * 1000, className: 'area-circle', weight: 2, dashArray: '6 6', fill: true, fillOpacity: .07, interactive: false }).addTo(map);
    },
    renderPins: function (items, spec) { items0 = items; spec0 = spec || null; drawPins(); },
    setCluster: function (on) { clusterOn = !!on; drawPins(); },
    getCluster: function () { return clusterOn; },
    getZoom: function () { return map.getZoom(); },

    /* ---- خط‌های مسیر + برچسب فاصله ----
       lines: [{from:{lat,lng}, to:{lat,lng}, cls, text}] */
    renderRoutes: function (lines) {
      routesLayer.clearLayers();
      lines.forEach(function (l) {
        L.polyline([[l.from.lat, l.from.lng], [l.to.lat, l.to.lng]], {
          className: 'rl ' + l.cls, weight: 3, interactive: false
        }).addTo(routesLayer);
        var m = NQ.geo.mid(l.from, l.to);
        L.marker([m.lat, m.lng], {
          interactive: false, keyboard: false, zIndexOffset: 500,
          icon: L.divIcon({
            className: 'rc', iconSize: [0, 0], iconAnchor: [0, 0],
            html: '<span class="rw"><span class="rchip ' + l.cls + '">' + l.text + '</span></span>'
          })
        }).addTo(routesLayer);
      });
    },

    /* ---- نمای نقشه ---- */
    fit: function (points) {
      var size = map.getSize();
      if (!size.x || !size.y) { pendingFit = points; return; }
      if (!points.length) { map.setView([NQ.CENTER.lat, NQ.CENTER.lng], 13, { animate: false }); return; }
      var b = L.latLngBounds(points.map(function (p) { return [p.lat, p.lng]; }));
      var free = Math.max(120, size.y - insets.t - insets.b);   // ارتفاع بخشی از نقشه که واقعاً دیده می‌شود
      map.fitBounds(b, {
        paddingTopLeft: [Math.min(44, size.x * .1), insets.t + Math.min(64, free * .2)],
        paddingBottomRight: [Math.min(44, size.x * .1) + Math.min(insets.r, size.x - 160), Math.min(insets.b, size.y - insets.t - 120) + Math.min(76, free * .24)],
        maxZoom: 16, animate: !reduced
      });
    },
    /* بخش‌هایی از بالا و پایین نقشه که زیر نوار جستجو یا صفحهٔ پایینِ موبایل پنهان است (پیکسل) */
    setInsets: function (i) { insets = { t: i.t || 0, b: i.b || 0, r: i.r || 0 }; },
    /* نقشه پنهان بوده (صفحهٔ فهرست/دستیار) و دوباره دیده می‌شود: اندازهٔ تازه خوانده شود */
    refresh: function () { if (map) map.invalidateSize({ animate: false }); },
    zoomIn: function () { map.zoomIn(); },
    zoomOut: function () { map.zoomOut(); },
    panTo: function (p) { map.panTo([p.lat, p.lng], { animate: !reduced }); },

    /* پین یک فروشگاه را (اگر بیرون از نما یا زیر کنترل‌ها باشد) با حداقل جابه‌جایی و فاصلهٔ pad پیکسل از لبه‌ها
       داخل نقشه می‌آورد. نقشه را وسط نمی‌گذارد؛ اگر پین از قبل کامل دیده می‌شود هیچ کاری نمی‌کند. */
    reveal: function (sid, ll, pad) {
      if (!map) return;
      pad = pad == null ? 20 : pad;
      var cb = map.getContainer().getBoundingClientRect();
      if (!cb.width || !cb.height) return;
      var box = { left: cb.left, right: Math.max(cb.left + 120, cb.right - insets.r), top: cb.top + insets.t, bottom: Math.max(cb.top + insets.t + 80, cb.bottom - insets.b) };
      var cur = pins[sid], el = cur && cur.marker.getElement(), pw = el && el.querySelector('.pw'), r;
      if (pw) { var b = pw.getBoundingClientRect(); r = { l: b.left, r: b.right, t: b.top, b: b.bottom }; }
      else if (ll) {   // پین دیده نمی‌شود (مثلاً داخل خوشه): اندازهٔ تقریبی برچسب بالای نقطه
        var pt = map.latLngToContainerPoint([ll.lat, ll.lng]);
        r = { l: box.left + pt.x - 36, r: box.left + pt.x + 36, t: box.top + pt.y - 40, b: box.top + pt.y };
      } else return;
      var sx = 0, sy = 0;   // چقدر باید پین روی صفحه جابه‌جا شود
      if (r.l < box.left + pad) sx = box.left + pad - r.l; else if (r.r > box.right - pad) sx = box.right - pad - r.r;
      if (r.t < box.top + pad) sy = box.top + pad - r.t; else if (r.b > box.bottom - pad) sy = box.bottom - pad - r.b;
      /* اگر بعد از جابه‌جایی زیر دکمه‌های کنترل یا راهنمای نقشه می‌افتد، کمی بیشتر جابه‌جا شود */
      var m = 12;
      Array.prototype.forEach.call(map.getContainer().parentNode.querySelectorAll('.ctl,.legend'), function (o) {
        if (o.hidden) return;
        var ob = o.getBoundingClientRect(); if (!ob.width) return;
        var n = { l: r.l + sx, r: r.r + sx, t: r.t + sy, b: r.b + sy };
        if (n.r < ob.left - m || n.l > ob.right + m || n.b < ob.top - m || n.t > ob.bottom + m) return;
        if (o.classList.contains('legend')) sy -= n.b - (ob.top - m);
        else {
          var dx = ob.right + m - n.l, dy = ob.bottom + m - n.t;
          if (dx <= dy) sx += dx; else sy += dy;
        }
      });
      if (Math.abs(sx) < 1 && Math.abs(sy) < 1) return;
      map.panBy([-sx, -sy], { animate: !reduced });
    },

    /* ---- موقعیت واقعی کاربر (GPS) ---- */
    locate: function (ok, fail) {
      if (!navigator.geolocation) { fail('unsupported'); return; }
      navigator.geolocation.getCurrentPosition(
        function (pos) { ok({ lat: pos.coords.latitude, lng: pos.coords.longitude }); },
        function (err) { fail(err && err.code === 1 ? 'denied' : 'failed'); },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
      );
    }
  };
})(window.NQ = window.NQ || {});
