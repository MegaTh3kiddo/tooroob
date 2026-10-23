'use client';

import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { STORES, OFFERS, PRODUCTS, ORIGIN, COLORS, STOCK_LABELS, CATS } from '../../data/mockData';
import { roadKm, travelMinutes, resolveMode, DEF_TRAVEL } from '../../services/travelService';
import { ICONS, SvgIcon } from '../../data/icons';
import { getProductArt, getStoreArt } from '../../data/art';
import { Product, Store, Offer } from '../../types';

export const ListView: React.FC = () => {
  const {
    activeCategory,
    setActiveCategory,
    selectedProduct,
    setSelectedProduct,
    filters,
    setFilters,
    planStops,
    togglePlanStop,
    removePlanStop,
    clearPlan,
    setStopDone,
    movePlanStop,
    compareSlots,
    setCompareSlot,
    clearCompareSlot,
    openModal,
    addInquiry,
    travelMode,
    setTravelMode,
    searchQuery,
    setSelectedStoreForMap,
    setView,
  } = useApp();

  const [activeTab, setActiveTab] = useState<'results' | 'plan'>('results');
  const [travelDropOpen, setTravelDropOpen] = useState(false);
  const [expandedStoreInfo, setExpandedStoreInfo] = useState<Record<string, boolean>>({});
  const [expandedProdDetails, setExpandedProdDetails] = useState<Record<string, boolean>>({});
  const [isPickBarOpen, setIsPickBarOpen] = useState(false);

  // Products available in current category
  const prods: Product[] = PRODUCTS[activeCategory.id] || [];

  // Toggle store card details
  const toggleStoreDetails = (sid: string) => {
    setExpandedStoreInfo((prev) => ({ ...prev, [sid]: !prev[sid] }));
  };

  // Toggle product card details in pick stage
  const toggleProdDetails = (pid: string) => {
    setExpandedProdDetails((prev) => ({ ...prev, [pid]: !prev[pid] }));
  };

  // Raw offers for current category
  const rawOffers: any[] = OFFERS[activeCategory.id] || [];

  // Offers filtered by current product (if a product is picked)
  const currentOffers = rawOffers.filter((o) => {
    if (!selectedProduct) return true;
    return o.title === selectedProduct.title || !o.title;
  });

  // Calculate km, eta, open status for offers
  const processedOffers = currentOffers
    .map((off) => {
      const store = STORES[off.storeId];
      if (!store) return null;

      const km = roadKm(ORIGIN, { lat: store.lat, lng: store.lng });
      const tm = travelMinutes(resolveMode(travelMode, km), km);

      const now = new Date();
      const currentH = now.getHours();
      const isOpen = currentH >= store.openH && currentH < store.closeH;

      return {
        ...off,
        store,
        km,
        travelMin: tm,
        isOpen,
      };
    })
    .filter(Boolean)
    .filter((item: any) => {
      if (searchQuery && !item.store.name.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false;
      }
      if (filters.torobpayOnly && !item.store.torobpay) return false;
      if (filters.guaranteeOnly && !item.store.guarantee) return false;
      if (filters.installmentsOnly && (!item.store.installments || item.store.installments.length === 0)) return false;
      if (filters.openNowOnly && !item.isOpen) return false;
      if (filters.fastOnly && !item.store.fast) return false;
      if (filters.minRating > 0 && item.store.rating < filters.minRating) return false;
      if (item.km > filters.maxDistance) return false;
      return true;
    })
    .sort((a: any, b: any) => {
      if (filters.sort === 'priceAsc') return a.price - b.price;
      if (filters.sort === 'distAsc') return a.km - b.km;
      if (filters.sort === 'ratingDesc') return b.store.rating - a.store.rating;
      // Smart ranking: combination of price, distance, and rating
      const scoreA = a.price / 1000000 + a.km * 2 - a.store.rating * 5;
      const scoreB = b.price / 1000000 + b.km * 2 - b.store.rating * 5;
      return scoreA - scoreB;
    });

  // Find min and max prices
  const minPrice = processedOffers.length > 0 ? Math.min(...processedOffers.map((o: any) => o.price)) : 0;
  const maxPrice = processedOffers.length > 0 ? Math.max(...processedOffers.map((o: any) => o.price)) : 0;
  const bestSid = processedOffers.length > 0 ? processedOffers[0]?.storeId : null;
  const nearSid = processedOffers.length > 0
    ? [...processedOffers].sort((a: any, b: any) => a.km - b.km)[0]?.storeId
    : null;

  const travelModes: { id: any; label: string }[] = [
    { id: 'auto', label: 'پیشنهادی' },
    { id: 'walk', label: 'پیاده' },
    { id: 'transit', label: 'اتوبوس یا مترو' },
    { id: 'car', label: 'ماشین' },
    { id: 'moto', label: 'موتور' },
  ];

  const activeFiltersCount =
    (filters.torobpayOnly ? 1 : 0) +
    (filters.guaranteeOnly ? 1 : 0) +
    (filters.installmentsOnly ? 1 : 0) +
    (filters.openNowOnly ? 1 : 0) +
    (filters.fastOnly ? 1 : 0) +
    (filters.minRating > 0 ? 1 : 0);

  return (
    <section className="list" id="list" aria-label="فروشگاه‌ها">
      {/* دستگیره کشیدن صفحه در موبایل */}
      <div className="sheet-grip" id="sheetGrip" role="button" tabIndex={0} aria-label="بالا و پایین بردن فهرست">
        <i></i>
      </div>
      <button className="sheet-peek" id="sheetPeek" type="button"></button>

      {/* تب‌های نتایج جستجو و برنامه سر زدن */}
      <div className="tabs" role="tablist" aria-label="نمایش">
        <button
          className="tab"
          id="tabResults"
          type="button"
          role="tab"
          aria-selected={activeTab === 'results'}
          onClick={() => setActiveTab('results')}
        >
          <span className="tab-ic" id="tabResIc" dangerouslySetInnerHTML={{ __html: ICONS.list }} />
          نتایج جستجو <span className="cnt n" id="resCount">{processedOffers.length.toLocaleString('fa-IR')}</span>
        </button>

        <button
          className="tab"
          id="tabPlan"
          type="button"
          role="tab"
          aria-selected={activeTab === 'plan'}
          onClick={() => setActiveTab('plan')}
        >
          <span className="tab-ic" id="tabPlanIc" dangerouslySetInnerHTML={{ __html: ICONS.bookmark }} />
          برنامهٔ سر زدن <span className="cnt" id="planCount">{planStops.length.toLocaleString('fa-IR')}</span>
        </button>
      </div>

      {/* نوار محصولِ انتخاب‌شده (PickBar) */}
      {selectedProduct && activeTab === 'results' && (
        <div className="pickbar" id="pickBar">
          <section className="sp" tabIndex={-1} aria-label={`محصول انتخاب‌شده: ${selectedProduct.title}`}>
            <div className="sp-main">
              <span
                className="sp-img gthumb"
                role="button"
                tabIndex={0}
                aria-label={`بزرگ کردن تصویر ${selectedProduct.title}`}
                onClick={() => openModal('gallery', selectedProduct)}
                dangerouslySetInnerHTML={{ __html: getProductArt(selectedProduct.kind || 'over', COLORS[selectedProduct.colors?.[0] || 'مشکی']) }}
              />

              <div className="sp-info">
                <span className="sp-name" data-full={selectedProduct.title}>
                  {selectedProduct.title}
                </span>
                <span className="sp-sub">
                  <span className="dots" aria-label={`رنگ‌ها: ${(selectedProduct.colors || ['مشکی', 'سفید']).join('، ')}`}>
                    {(selectedProduct.colors || ['مشکی', 'سفید']).map((c) => (
                      <i key={c} className="sw" style={{ background: COLORS[c] || '#8C9692' }} title={c} />
                    ))}
                  </span>
                  <span>{processedOffers.length.toLocaleString('fa-IR')} فروشگاه</span>
                  {minPrice > 0 && (
                    <span>
                      از <b>{minPrice.toLocaleString('fa-IR')}</b> تومان
                    </span>
                  )}
                </span>
              </div>

              <button
                type="button"
                className="cmp-ic"
                id="spCmp"
                aria-label="مقایسه با محصول دیگر"
                title="مقایسه با محصول دیگر"
                onClick={() => openModal('spec', selectedProduct)}
                dangerouslySetInnerHTML={{ __html: ICONS.group }}
              />

              <button
                type="button"
                className="sp-change"
                id="spChange"
                onClick={() => setSelectedProduct(null)}
              >
                تغییر محصول
              </button>
            </div>

            <button
              type="button"
              className="sp-more"
              id="spMore"
              aria-expanded={isPickBarOpen}
              aria-controls="spPanel"
              onClick={() => setIsPickBarOpen(!isPickBarOpen)}
            >
              <span>مشاهدهٔ جزئیات</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>

            {isPickBarOpen && (
              <div className="sp-panel" id="spPanel">
                <p className="sp-desc">{selectedProduct.desc || selectedProduct.tagline}</p>
                <button
                  type="button"
                  className="pr-go-btn"
                  onClick={() => openModal('spec', selectedProduct)}
                >
                  مشخصات کامل فنی
                </button>
              </div>
            )}
          </section>
        </div>
      )}

      {/* نوار تنظیمات رفت‌وآمد، فیلترها و مقایسه */}
      {activeTab === 'results' && (
        <div className="travel" id="travel">
          <span className="travel-l">رفت‌وآمد:</span>
          <div className="tdrop" id="tdrop">
            <button
              className="tdrop-btn"
              id="tBtn"
              type="button"
              aria-haspopup="listbox"
              aria-expanded={travelDropOpen}
              aria-controls="tPop"
              onClick={() => setTravelDropOpen(!travelDropOpen)}
            >
              {travelModes.find((m) => m.id === travelMode)?.label || 'پیشنهادی'}
            </button>
            {travelDropOpen && (
              <ul className="tdrop-pop" id="tPop" role="listbox" aria-label="روش رفت‌وآمد">
                {travelModes.map((m) => (
                  <li
                    key={m.id}
                    className={`topt ${travelMode === m.id ? 'sel' : ''}`}
                    onClick={() => {
                      setTravelMode(m.id);
                      setTravelDropOpen(false);
                    }}
                  >
                    {m.label}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <button
            className="cmp-ic bordered help-btn"
            id="helpBtn"
            type="button"
            aria-haspopup="dialog"
            aria-controls="helpDlg"
            aria-label="راهنمای ترب"
            title="راهنمای ترب"
            onClick={() => openModal('help')}
            dangerouslySetInnerHTML={{ __html: ICONS.info }}
          />

          <button
            className="cmp-ic bordered"
            id="cmpToggle"
            type="button"
            aria-pressed={!!(compareSlots.a || compareSlots.b)}
            aria-label="مقایسهٔ دو فروشگاه"
            title="مقایسهٔ دو فروشگاه"
            onClick={() => {
              if (compareSlots.a && compareSlots.b) {
                openModal('cmp', { slotA: compareSlots.a, slotB: compareSlots.b });
              }
            }}
          >
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M16 3l4 4-4 4" />
              <path d="M20 7H8" />
              <path d="M8 21l-4-4 4-4" />
              <path d="M4 17h12" />
            </svg>
          </button>

          <button
            className="filter-btn"
            id="filterBtn"
            type="button"
            aria-haspopup="dialog"
            aria-controls="filterDlg"
            onClick={() => openModal('filter')}
          >
            <span className="filter-ic" id="filterIc" dangerouslySetInnerHTML={{ __html: ICONS.filter }} />
            <span>فیلتر</span>
            <b className="fcnt" id="fCount" hidden={activeFiltersCount === 0}>
              {activeFiltersCount.toLocaleString('fa-IR')}
            </b>
          </button>
        </div>
      )}

      {/* نوار ابزار: آمار خلاصه و مرتب‌سازی */}
      {activeTab === 'results' && (
        <div className="toolbar" id="toolbar">
          <p className="summary" id="summary" aria-live="polite">
            <b>{processedOffers.length.toLocaleString('fa-IR')} فروشگاه</b> برای {selectedProduct ? selectedProduct.title : activeCategory.name}
            {minPrice > 0 && (
              <span> · قیمت از {Math.round(minPrice / 1000).toLocaleString('fa-IR')} تا {Math.round(maxPrice / 1000).toLocaleString('fa-IR')} هزار تومان</span>
            )}
          </p>

          <div className="seg" id="sort" role="radiogroup" aria-label="مرتب‌سازی">
            <button
              type="button"
              role="radio"
              data-sort="price"
              aria-checked={filters.sort === 'priceAsc'}
              onClick={() => setFilters((f) => ({ ...f, sort: 'priceAsc' }))}
            >
              ارزان‌ترین
            </button>
            <button
              type="button"
              role="radio"
              data-sort="near"
              aria-checked={filters.sort === 'distAsc'}
              onClick={() => setFilters((f) => ({ ...f, sort: 'distAsc' }))}
            >
              نزدیک‌ترین
            </button>
            <button
              type="button"
              role="radio"
              data-sort="smart"
              aria-checked={filters.sort === 'smart'}
              onClick={() => setFilters((f) => ({ ...f, sort: 'smart' }))}
            >
              پیشنهادی
            </button>
          </div>

          <div className="fchips" id="fChips" aria-label="فیلترهای فعال">
            {filters.torobpayOnly && <span className="fchip">ترب‌پی</span>}
            {filters.guaranteeOnly && <span className="fchip">ضمانت ترب</span>}
            {filters.openNowOnly && <span className="fchip">فروشگاه‌های باز</span>}
            {filters.fastOnly && <span className="fchip">ارسال فوری</span>}
          </div>
        </div>
      )}

      {/* بخش اسکرول: محصولات (اگر محصولی انتخاب نشده) یا فروشگاه‌ها */}
      {activeTab === 'results' && (
        <div className="scroll" id="scroll">
          <div id="pcmp"></div>

          {/* حالت ۱: انتخاب مدل محصول (Pick stage) */}
          {!selectedProduct && (
            <ul className="prods" id="prods" aria-label="محصولات">
              {prods.map((p, i) => {
                const open = !!expandedProdDetails[p.id];
                const artSvg = getProductArt(p.kind || 'over', COLORS[p.colors?.[0] || 'مشکی']);
                return (
                  <li key={p.id} style={{ '--i': i } as any}>
                    <article className={`prod ${open ? 'open' : ''}`} data-id={p.id}>
                      <button
                        type="button"
                        className="prod-main"
                        data-prod={p.id}
                        aria-label={`دیدن فروشگاه‌های ${p.title}`}
                        onClick={() => setSelectedProduct(p)}
                      >
                        <span
                          className="pr-img gthumb"
                          role="button"
                          tabIndex={0}
                          dangerouslySetInnerHTML={{ __html: artSvg }}
                        />

                        <span className="pr-body">
                          <span className="pr-row">
                            <span className="pr-name" data-full={p.title}>{p.title}</span>
                            {i === 0 && <span className="tag best">ارزان‌ترین</span>}
                          </span>
                          <span className="pr-desc">{p.tagline || ''}</span>
                          <span className="pr-price">
                            <small>از</small> <b>{(3890000 + i * 250000).toLocaleString('fa-IR')}</b> <small>تومان</small>
                          </span>
                          <span className="pr-meta">
                            <span className="dots">
                              {(p.colors || ['مشکی', 'سفید']).map((c) => (
                                <i key={c} className="sw" style={{ background: COLORS[c] || '#8C9692' }} title={c} />
                              ))}
                            </span>
                            <span>{processedOffers.length.toLocaleString('fa-IR')} فروشگاه</span>
                          </span>
                        </span>

                        <svg className="chev-go" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <path d="M15 18l-6-6 6-6" />
                        </svg>
                      </button>

                      <div className="pr-foot">
                        <button
                          type="button"
                          className="pr-more"
                          data-pinfo={p.id}
                          aria-expanded={open}
                          onClick={() => toggleProdDetails(p.id)}
                        >
                          <SvgIcon name="info" size={16} />
                          <span>مشاهدهٔ جزئیات</span>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                            <path d="M6 9l6 6 6-6" />
                          </svg>
                        </button>
                      </div>

                      {open && (
                        <div className="pr-det" id={`pd-${p.id}`}>
                          <p className="pr-range">
                            <span>قیمت در فروشگاه‌ها</span>
                            <b>از ۳,۸۹۰,۰۰۰ تا ۴,۶۰۰,۰۰۰ تومان</b>
                          </p>
                          <p className="pr-desc">{p.desc}</p>
                          <button
                            type="button"
                            className="pr-go-btn"
                            onClick={() => setSelectedProduct(p)}
                          >
                            دیدن فروشگاه‌ها روی نقشه
                          </button>
                        </div>
                      )}
                    </article>
                  </li>
                );
              })}
            </ul>
          )}

          <div id="cmp"></div>

          {/* حالت ۲: نمایش کارت‌های فروشگاه‌ها (Stores offers) */}
          {selectedProduct && (
            <ul className="cards" id="cards">
              {processedOffers.map((o: any, i: number) => {
                const sid = o.storeId;
                const isInfoOpen = !!expandedStoreInfo[sid];
                const isSaved = planStops.some((s) => s.sid === sid);
                const isCompA = compareSlots.a?.storeName === o.store.name;
                const isCompB = compareSlots.b?.storeName === o.store.name;
                const slotClass = isCompA ? 'slot-a' : isCompB ? 'slot-b' : '';

                return (
                  <li key={`${sid}_${i}`} style={{ '--i': Math.min(i, 10) } as any}>
                    <article className={`card in ${slotClass}`} data-sid={sid}>
                      <button
                        type="button"
                        className="card-main"
                        data-sid={sid}
                        aria-pressed={isInfoOpen || isCompA || isCompB}
                        onClick={() => toggleStoreDetails(sid)}
                      >
                        <span className="c-body">
                          <span className="c-row">
                            <span className="c-nm">
                              {o.store.guarantee && (
                                <span className="torob-guarantee" role="link" tabIndex={-1} aria-label="ضمانت ترب">
                                  <span className="styles_hologram__5u9vV" style={{ width: 24, height: 24 }}>
                                    <span className="styles_star__jo3q8">
                                      <span className="styles_wavyPattern__3a8qy">
                                        <span className="styles_wavyPatternLight__7Ymlp"></span>
                                      </span>
                                    </span>
                                    <span className="styles_torobLogo__rNXpC">
                                      <span className="styles_torobLogoLight__xQOQ_"></span>
                                    </span>
                                  </span>
                                </span>
                              )}
                              {o.store.torobpay && (
                                <span className="pay tp" dangerouslySetInnerHTML={{ __html: ICONS.torobpay }} />
                              )}
                              <span className="c-name" data-full={o.store.name}>
                                {o.store.name}
                              </span>
                            </span>

                            {o.store.fast && (
                              <span className="tag fast" data-hint={o.store.fast}>
                                <SvgIcon name="truck" size={14} />
                                ارسال فوری
                              </span>
                            )}
                            {sid === bestSid && <span className="tag best">ارزان‌ترین</span>}
                            {sid === nearSid && <span className="tag near">نزدیک‌ترین</span>}
                          </span>

                          <span className="c-var">
                            <span className="dots">
                              {(selectedProduct.colors || ['مشکی']).map((c) => (
                                <i key={c} className="sw" style={{ background: COLORS[c] || '#8C9692' }} title={c} />
                              ))}
                            </span>
                            {o.store.rating && (
                              <span className="rate">
                                <SvgIcon name="star" size={14} />
                                <b>{o.store.rating.toLocaleString('fa-IR', { minimumFractionDigits: 1 })}</b>
                                <small>({o.store.years.toLocaleString('fa-IR')} سال در ترب)</small>
                              </span>
                            )}
                          </span>

                          <span className="c-meta">
                            <span className="stock in">موجود و بروز</span>
                            <span className={`status ${o.isOpen ? 'open' : 'closed'}`}>
                              {o.isOpen ? 'باز است' : 'بسته'}
                            </span>
                            <span>{Number(o.km.toFixed(1)).toLocaleString('fa-IR')} کیلومتر</span>
                            <span className="eta">
                              <SvgIcon name="car" size={14} />
                              <span>{o.travelMin.toLocaleString('fa-IR')} دقیقه</span>
                            </span>
                          </span>
                        </span>

                        <span className="c-price">
                          <b>{o.price.toLocaleString('fa-IR')}</b>
                          <small>تومان</small>
                          <span className="upd">
                            <span>بروزرسانی ۲ ساعت پیش</span>
                            <SvgIcon name="clock" size={14} />
                          </span>
                        </span>
                      </button>

                      {/* دکمه بوکمارک / سر زدن */}
                      <button
                        type="button"
                        className="save-btn"
                        data-save={sid}
                        aria-pressed={isSaved}
                        aria-label={isSaved ? 'برداشتن از برنامهٔ سر زدن' : 'ذخیره در برنامهٔ سر زدن'}
                        title={isSaved ? 'برداشتن از برنامهٔ سر زدن' : 'ذخیره در برنامهٔ سر زدن'}
                        onClick={() => togglePlanStop(sid, activeCategory.id)}
                      >
                        <svg width="19" height="19" viewBox="0 0 24 24" fill={isSaved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                          <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z" />
                        </svg>
                      </button>

                      {/* دکمه اطلاعات کامل فروشگاه */}
                      <button
                        type="button"
                        className="info-btn"
                        data-sinfo={sid}
                        aria-expanded={isInfoOpen}
                        aria-label={isInfoOpen ? 'بستن اطلاعات فروشگاه' : 'اطلاعات کامل فروشگاه'}
                        title={isInfoOpen ? 'بستن اطلاعات' : 'اطلاعات کامل فروشگاه'}
                        onClick={() => toggleStoreDetails(sid)}
                        dangerouslySetInnerHTML={{ __html: ICONS.info }}
                      />

                      {/* پنل جزئیات بازشونده دقیق مطابق storeDetHTML */}
                      {isInfoOpen && (
                        <dl className="det">
                          <dt>نشانی</dt>
                          <dd>{o.store.addr}</dd>

                          <dt>ساعت کار</dt>
                          <dd>{o.store.hours} <span className={`status ${o.isOpen ? 'open' : 'closed'}`}>{o.isOpen ? 'باز است' : 'بسته است'}</span></dd>

                          <dt>تلفن</dt>
                          <dd className="tels">
                            {(o.store.phones || [o.store.phone]).map((p: string, pidx: number) => (
                              <React.Fragment key={p}>
                                <a className="tel" href={`tel:${p.replace(/[^0-9]/g, '')}`} dir="ltr" aria-label={`تماس با ${p}`}>
                                  {p}
                                </a>
                                {pidx < (o.store.phones || []).length - 1 && <i className="rsep">·</i>}
                              </React.Fragment>
                            ))}
                          </dd>

                          {o.store.fast && (
                            <>
                              <dt>ارسال</dt>
                              <dd className="fastv">
                                <SvgIcon name="truck" size={14} />
                                {o.store.fast}
                              </dd>
                            </>
                          )}

                          <dt>اعتبار</dt>
                          <dd className="score-row">
                            <span>امتیاز رضایت: ★ {o.store.rating}</span> · <span>{o.store.orders90} سفارش اخیر</span>
                          </dd>

                          {/* ردیف دکمه‌های عملیاتی اصلی */}
                          <dd className="wide-row">
                            <div className="acts">
                              <button
                                type="button"
                                className="act-btn call"
                                onClick={() => openModal('call', o.store)}
                              >
                                <SvgIcon name="phone" size={16} />
                                <span>تماس</span>
                              </button>

                              <button
                                type="button"
                                className="act-btn inq"
                                onClick={() => addInquiry(sid, selectedProduct?.id)}
                              >
                                <SvgIcon name="inquiry" size={16} />
                                <span>استعلام</span>
                              </button>

                              <button
                                type="button"
                                className="act-btn route"
                                onClick={() => {
                                  setSelectedStoreForMap(sid);
                                  setView('map');
                                }}
                              >
                                <SvgIcon name="route" size={16} />
                                <span>مسیریابی</span>
                              </button>

                              <button
                                type="button"
                                className={`act-btn cmp ${isCompA || isCompB ? 'active' : ''}`}
                                onClick={() => {
                                  if (!compareSlots.a) {
                                    setCompareSlot('a', { offer: o, product: selectedProduct, storeName: o.store.name });
                                  } else if (!compareSlots.b) {
                                    setCompareSlot('b', { offer: o, product: selectedProduct, storeName: o.store.name });
                                  } else {
                                    setCompareSlot('a', { offer: o, product: selectedProduct, storeName: o.store.name });
                                  }
                                }}
                              >
                                <span>{isCompA ? 'انتخاب اول' : isCompB ? 'انتخاب دوم' : 'مقایسه'}</span>
                              </button>
                            </div>
                          </dd>

                          <dd className="wide-row det-foot">
                            <button
                              type="button"
                              className="report-btn"
                              data-report={sid}
                              onClick={() => openModal('report', o.store)}
                            >
                              <SvgIcon name="flag" size={14} />
                              <span>گزارش مشکل فروشگاه</span>
                            </button>
                          </dd>
                        </dl>
                      )}
                    </article>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      {/* تب برنامهٔ سر زدن (#tabPlan) */}
      {activeTab === 'plan' && (
        <>
          <div className="planbar" id="planbar">
            <p className="summary" id="planSummary" aria-live="polite">
              <b>{planStops.length.toLocaleString('fa-IR')} فروشگاه</b> در برنامهٔ سر زدن شما ذخیره شده است.
            </p>
            <div className="seg" id="planSort" role="radiogroup" aria-label="ترتیب سر زدن">
              <button type="button" role="radio" data-pmode="near" aria-checked="false">نزدیک‌ترین اول</button>
              <button type="button" role="radio" data-pmode="closing" aria-checked="false">زودتر می‌بندد</button>
              <button type="button" role="radio" data-pmode="smart" aria-checked="true">مسیر هوشمند</button>
            </div>
            <div className="opts">
              <button type="button" className="link-btn" id="planClear" onClick={clearPlan}>
                پاک‌کردن همه
              </button>
            </div>
          </div>

          <div className="scroll" id="planScroll">
            <div id="planCmp"></div>
            {planStops.length === 0 ? (
              <div className="as-empty" style={{ padding: '40px 20px', textAlign: 'center' }}>
                <p>هنوز فروشگاهی در برنامهٔ سر زدن ذخیره نشده است.</p>
                <span style={{ fontSize: 13, color: 'var(--muted)' }}>
                  روی آیکون نشان کردن در هر کارت فروشگاه بزنید تا به این فهرست اضافه شود.
                </span>
              </div>
            ) : (
              <ul className="plan-list" id="planList">
                {planStops.map((ps, idx) => {
                  const store = STORES[ps.sid];
                  if (!store) return null;
                  const km = roadKm(ORIGIN, { lat: store.lat, lng: store.lng });
                  return (
                    <li key={ps.sid} className={`plan-item ${ps.done ? 'is-done' : ''}`}>
                      <div className="as-stop-num">{idx + 1}</div>
                      <div className="as-stop-info">
                        <h4 className="as-stop-name">{store.name}</h4>
                        <p className="as-stop-addr">{store.addr}</p>
                        <span className="as-stop-meta">{Number(km.toFixed(1)).toLocaleString('fa-IR')} کیلومتر</span>
                      </div>
                      <div className="as-stop-actions">
                        <button
                          type="button"
                          className="as-btn check"
                          title="علامت‌گذاری سر زده شده"
                          onClick={() => setStopDone(ps.sid, !ps.done)}
                        >
                          ✓
                        </button>
                        <button
                          type="button"
                          className="as-btn del"
                          title="حذف"
                          onClick={() => removePlanStop(ps.sid)}
                        >
                          ×
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </>
      )}
    </section>
  );
};
