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
  var map, pinsLayer, routesLayer, youMarker, handlers = {}, pins = {}, pendingFit = null;

  function pinIcon(p) {
    return L.divIcon({
      className: 'pin ' + p.cls,
      html: '<span class="pw">' + p.html + '</span>',
      iconSize: [0, 0], iconAnchor: [0, 0]
    });
  }
  function decorate(marker, label) {
    var el = marker.getElement();
    if (el) { el.setAttribute('aria-label', label); el.setAttribute('role', 'button'); }
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
      L.control.scale({ imperial: false, position: 'bottomright' }).addTo(map);

      routesLayer = L.layerGroup().addTo(map);
      pinsLayer = L.layerGroup().addTo(map);

      map.on('click', function () { if (handlers.onBackgroundClick) handlers.onBackgroundClick(); });

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
       items: [{sid, lat, lng, cls, html, label, z}] — مارکرها حفظ می‌شوند و فقط در صورت تغییر آیکون عوض می‌شود. */
    renderPins: function (items) {
      var focused = null, ae = document.activeElement;
      Object.keys(pins).forEach(function (sid) { if (pins[sid].marker.getElement() === ae) focused = sid; });

      var keep = {};
      items.forEach(function (p) {
        keep[p.sid] = true;
        var sig = p.cls + '|' + p.html, cur = pins[p.sid];
        if (!cur) {
          var m = L.marker([p.lat, p.lng], { icon: pinIcon(p), keyboard: true, zIndexOffset: p.z });
          m.on('click', function () { if (handlers.onPinClick) handlers.onPinClick(p.sid); });
          m.addTo(pinsLayer);
          decorate(m, p.label);
          pins[p.sid] = { marker: m, sig: sig };
        } else {
          if (cur.sig !== sig) { cur.marker.setIcon(pinIcon(p)); decorate(cur.marker, p.label); cur.sig = sig; }
          cur.marker.setZIndexOffset(p.z);
        }
      });
      Object.keys(pins).forEach(function (sid) {
        if (!keep[sid]) { pinsLayer.removeLayer(pins[sid].marker); delete pins[sid]; }
      });
      if (focused && pins[focused]) {
        var el = pins[focused].marker.getElement();
        if (el && el !== document.activeElement) el.focus({ preventScroll: true });
      }
    },

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
      map.fitBounds(b, {
        paddingTopLeft: [Math.min(44, size.x * .1), Math.min(64, size.y * .2)],
        paddingBottomRight: [Math.min(44, size.x * .1), Math.min(76, size.y * .24)],
        maxZoom: 16, animate: !reduced
      });
    },
    zoomIn: function () { map.zoomIn(); },
    zoomOut: function () { map.zoomOut(); },
    panTo: function (p) { map.panTo([p.lat, p.lng], { animate: !reduced }); },

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
