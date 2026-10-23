'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useApp } from '../../context/AppContext';
import { CENTER, ORIGIN, STORES, OFFERS, CATS } from '../../data/mockData';
import { ICONS, SvgIcon } from '../../data/icons';
import { roadKm, travelMinutes, resolveMode } from '../../services/travelService';

export const MapView: React.FC = () => {
  const {
    activeCategory,
    planStops,
    togglePlanStop,
    openModal,
    addInquiry,
    selectedStoreForMap,
    setSelectedStoreForMap,
    travelMode,
  } = useApp();

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<any>(null);
  const markersRef = useRef<{ [sid: string]: any }>({});
  const polylineRef = useRef<any>(null);

  const [activeStoreId, setActiveStoreId] = useState<string | null>(selectedStoreForMap);

  // Initialize Leaflet map dynamically on client
  useEffect(() => {
    if (typeof window === 'undefined' || !mapContainerRef.current) return;

    async function initMap() {
      const L = (await import('leaflet')).default;

      if (!mapContainerRef.current || leafletMapRef.current) return;

      const map = L.map(mapContainerRef.current, {
        center: [CENTER.lat, CENTER.lng],
        zoom: 13,
        zoomControl: false,
        minZoom: 3,
        maxZoom: 19,
        zoomSnap: 0.5,
      });

      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
        maxZoom: 19,
        referrerPolicy: 'strict-origin-when-cross-origin',
      }).addTo(map);

      // User location marker matching static UI (.you)
      const userIcon = L.divIcon({
        className: 'you-wrap',
        html: `<span class="you" role="button" tabindex="0" title="موقعیت شما"><span>شما</span></span>`,
        iconSize: [44, 44],
        iconAnchor: [22, 22],
      });

      L.marker([ORIGIN.lat, ORIGIN.lng], { icon: userIcon }).addTo(map);

      leafletMapRef.current = map;
      setTimeout(() => {
        map.invalidateSize();
      }, 100);
      renderStoreMarkers(L, map);
    }

    initMap();

    return () => {
      if (leafletMapRef.current) {
        leafletMapRef.current.remove();
        leafletMapRef.current = null;
      }
    };
  }, []);

  const renderStoreMarkers = useCallback((L: any, map: any) => {
    Object.values(markersRef.current).forEach((m) => m.remove());
    markersRef.current = {};

    const categoryOffers = OFFERS[activeCategory.id] || [];

    categoryOffers.forEach((off: any) => {
      const store = STORES[off.storeId];
      if (!store) return;

      const isSelected = activeStoreId === off.storeId;
      const isPlanned = planStops.some((s) => s.sid === off.storeId);

      const cls = `pin ${off.stock || 'in'} ${isSelected ? 'sel' : ''} ${isPlanned ? 'saved' : ''}`;
      const priceK = Math.round(off.price / 1000).toLocaleString('fa-IR');
      const pinHtml = `<span class="pp">${priceK}</span>`;

      const customIcon = L.divIcon({
        className: cls,
        html: pinHtml,
        iconSize: [56, 32],
        iconAnchor: [28, 32],
      });

      const marker = L.marker([store.lat, store.lng], { icon: customIcon }).addTo(map);

      marker.on('click', () => {
        setActiveStoreId(off.storeId);
        setSelectedStoreForMap(off.storeId);
      });

      markersRef.current[off.storeId] = marker;
    });

    // Render polyline route connecting plan stops
    if (polylineRef.current) {
      polylineRef.current.remove();
      polylineRef.current = null;
    }

    if (planStops.length > 0) {
      const latlngs: [number, number][] = [[ORIGIN.lat, ORIGIN.lng]];
      planStops.forEach((ps) => {
        const st = STORES[ps.sid];
        if (st) latlngs.push([st.lat, st.lng]);
      });

      polylineRef.current = L.polyline(latlngs, {
        color: '#EF4056',
        weight: 4,
        opacity: 0.8,
        dashArray: '6, 8',
      }).addTo(map);
    }
  }, [activeCategory.id, activeStoreId, planStops, setSelectedStoreForMap]);

  // Update store markers & polyline
  useEffect(() => {
    if (!leafletMapRef.current || typeof window === 'undefined') return;

    import('leaflet').then((LModule) => {
      const L = LModule.default;
      renderStoreMarkers(L, leafletMapRef.current);
    });
  }, [renderStoreMarkers]);

  // Active store details
  const currentStore = activeStoreId ? STORES[activeStoreId] : null;
  const currentOffer = activeStoreId
    ? (OFFERS[activeCategory.id] || []).find((o: any) => o.storeId === activeStoreId)
    : null;
  const currentKm = currentStore ? roadKm(ORIGIN, { lat: currentStore.lat, lng: currentStore.lng }) : 0;
  const currentTm = currentStore ? travelMinutes(resolveMode(travelMode, currentKm), currentKm) : 0;
  const isPlanSaved = activeStoreId ? planStops.some((s) => s.sid === activeStoreId) : false;

  return (
    <section className="map" id="map" aria-label="نقشهٔ فروشگاه‌ها">
      <div id="lmap" ref={mapContainerRef}></div>

      {/* ابزارهای کنترل نقشه (.ctl) دقیقاً مطابق index.html */}
      <div className="ctl">
        <button
          type="button"
          id="zin"
          aria-label="بزرگ‌نمایی"
          onClick={() => leafletMapRef.current?.zoomIn()}
        >
          +
        </button>
        <button
          type="button"
          id="zout"
          aria-label="کوچک‌نمایی"
          onClick={() => leafletMapRef.current?.zoomOut()}
        >
          −
        </button>
        <button
          type="button"
          id="zfit"
          aria-label="نمایش همهٔ نتایج"
          onClick={() => leafletMapRef.current?.setView([ORIGIN.lat, ORIGIN.lng], 13)}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4" />
          </svg>
        </button>
        <button
          type="button"
          id="zclu"
          aria-pressed="true"
          aria-label="گروه‌بندی فروشگاه‌های نزدیک هم"
          title="گروه‌بندی فروشگاه‌های نزدیک هم"
          dangerouslySetInnerHTML={{ __html: ICONS.group }}
        />
        <button
          type="button"
          id="zloc"
          aria-label="موقعیت من"
          onClick={() => leafletMapRef.current?.flyTo([ORIGIN.lat, ORIGIN.lng], 15)}
        >
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <circle cx="12" cy="12" r="3.5" />
            <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
            <circle cx="12" cy="12" r="8" />
          </svg>
        </button>
      </div>

      <button className="area-btn" id="areaBtn" type="button" hidden></button>
      <div className="area-pill" id="areaPill" hidden></div>
      <p className="hint" id="hint">نقطهٔ «شما» را بکشید تا موقعیت عوض شود</p>

      {/* کارت پیش‌نمایش فروشگاه انتخاب‌شده در نقشه */}
      {currentStore && currentOffer && (
        <div className="card sel map-preview-card" style={{ position: 'absolute', bottom: 20, right: 20, left: 20, zIndex: 1000, maxWidth: 420, margin: '0 auto' }}>
          <button
            type="button"
            className="card-main"
            onClick={() => openModal('store', currentStore)}
          >
            <span className="c-body">
              <span className="c-row">
                <span className="c-nm">
                  {currentStore.guarantee && (
                    <span className="torob-guarantee" role="link" tabIndex={-1}>
                      <span className="styles_hologram__5u9vV" style={{ width: 24, height: 24 }}>
                        <span className="styles_star__jo3q8"><span className="styles_wavyPattern__3a8qy"><span className="styles_wavyPatternLight__7Ymlp"></span></span></span>
                        <span className="styles_torobLogo__rNXpC"><span className="styles_torobLogoLight__xQOQ_"></span></span>
                      </span>
                    </span>
                  )}
                  <span className="c-name">{currentStore.name}</span>
                </span>
              </span>
              <span className="c-var">
                {currentStore.rating && (
                  <span className="rate">
                    <SvgIcon name="star" size={14} />
                    <b>{currentStore.rating.toLocaleString('fa-IR', { minimumFractionDigits: 1 })}</b>
                  </span>
                )}
              </span>
              <span className="c-meta">
                <span>{Number(currentKm.toFixed(1)).toLocaleString('fa-IR')} کیلومتر</span>
                <span className="eta">
                  <SvgIcon name="car" size={14} />
                  <span>{currentTm.toLocaleString('fa-IR')} دقیقه</span>
                </span>
              </span>
            </span>
            <span className="c-price">
              <b>{currentOffer.price.toLocaleString('fa-IR')}</b>
              <small>تومان</small>
            </span>
          </button>

          <button
            type="button"
            className="save-btn"
            aria-pressed={isPlanSaved}
            onClick={() => togglePlanStop(activeStoreId!, activeCategory.id)}
            title={isPlanSaved ? 'برداشتن از سر زدن‌ها' : 'افزودن به سر زدن‌ها'}
          >
            <svg width="19" height="19" viewBox="0 0 24 24" fill={isPlanSaved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z" />
            </svg>
          </button>

          <button
            type="button"
            className="info-btn"
            onClick={() => {
              setActiveStoreId(null);
              setSelectedStoreForMap(null);
            }}
            title="بستن"
          >
            ×
          </button>
        </div>
      )}
    </section>
  );
};
