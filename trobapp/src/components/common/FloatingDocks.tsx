'use client';

import React from 'react';
import { useApp } from '../../context/AppContext';
import { calculateSchedule, roadKm } from '../../services/travelService';
import { ORIGIN, COLORS } from '../../data/mockData';
import { ICONS, SvgIcon } from '../../data/icons';

export const FloatingDocks: React.FC = () => {
  const {
    compareSlots,
    clearCompareSlot,
    planStops,
    clearPlan,
    setIsVisitsOpen,
    openModal,
    travelMode,
  } = useApp();

  const slotA = compareSlots.a;
  const slotB = compareSlots.b;
  const hasCompare = !!(slotA || slotB);

  // If both are present, calculate road distance between them
  const distBetween =
    slotA?.offer?.store && slotB?.offer?.store
      ? roadKm(
          { lat: slotA.offer.store.lat, lng: slotA.offer.store.lng },
          { lat: slotB.offer.store.lat, lng: slotB.offer.store.lng }
        )
      : 0;

  if (!hasCompare) return null;

  return (
    <section className="cmp" id="cmp" aria-label="مقایسهٔ دو فروشگاه">
      <div className="cmp-head">
        <h2>مقایسهٔ دو فروشگاه</h2>
        <button
          type="button"
          className="cmp-close"
          id="cmpClose"
          onClick={() => {
            clearCompareSlot('a');
            clearCompareSlot('b');
          }}
        >
          بستن
        </button>
      </div>

      <div className="slots">
        {/* اسلات اولی (A) */}
        {slotA ? (
          <div className="slot a">
            <div className="s-top">
              <b className="lt a">اولی</b>
              <span className="s-name" data-full={slotA.storeName}>
                {slotA.storeName}
              </span>
              <button
                type="button"
                className="s-x"
                aria-label="حذف فروشگاه اولی"
                onClick={() => clearCompareSlot('a')}
              >
                ×
              </button>
            </div>
            <span className="c-var">
              <span className="c-model">{slotA.product?.title || ''}</span>
              <span>·</span>
              <span className="dots">
                {(slotA.product?.colors || ['مشکی']).map((c) => (
                  <i key={c} className="sw" style={{ background: COLORS[c] || '#8C9692' }} title={c} />
                ))}
              </span>
            </span>
            <span className="s-price">
              <b>{slotA.offer.price.toLocaleString('fa-IR')}</b> تومان
            </span>
            <span className="stock in">موجود و بروز</span>
            <span className="s-dist">
              {Number(slotA.offer.km?.toFixed(1) || 1.2).toLocaleString('fa-IR')} کیلومتر تا شما
            </span>
          </div>
        ) : (
          <div className="slot empty">
            <b className="lt a">اولی</b>
            <span>فروشگاه اولی را از لیست یا نقشه انتخاب کنید</span>
          </div>
        )}

        {/* اسلات دومی (B) */}
        {slotB ? (
          <div className="slot b">
            <div className="s-top">
              <b className="lt b">دومی</b>
              <span className="s-name" data-full={slotB.storeName}>
                {slotB.storeName}
              </span>
              <button
                type="button"
                className="s-x"
                aria-label="حذف فروشگاه دومی"
                onClick={() => clearCompareSlot('b')}
              >
                ×
              </button>
            </div>
            <span className="c-var">
              <span className="c-model">{slotB.product?.title || ''}</span>
              <span>·</span>
              <span className="dots">
                {(slotB.product?.colors || ['مشکی']).map((c) => (
                  <i key={c} className="sw" style={{ background: COLORS[c] || '#8C9692' }} title={c} />
                ))}
              </span>
            </span>
            <span className="s-price">
              <b>{slotB.offer.price.toLocaleString('fa-IR')}</b> تومان
            </span>
            <span className="stock in">موجود و بروز</span>
            <span className="s-dist">
              {Number(slotB.offer.km?.toFixed(1) || 2.4).toLocaleString('fa-IR')} کیلومتر تا شما
            </span>
          </div>
        ) : (
          <div className="slot empty">
            <b className="lt b">دومی</b>
            <span>فروشگاه دومی را انتخاب کنید</span>
          </div>
        )}
      </div>

      {slotA && slotB ? (
        <>
          <dl className="facts">
            <div>
              <dt>فاصلهٔ دو فروشگاه از هم</dt>
              <dd>{Number(distBetween.toFixed(1)).toLocaleString('fa-IR')} کیلومتر</dd>
            </div>
            <div>
              <dt>اختلاف قیمت</dt>
              <dd>
                {Math.abs(slotA.offer.price - slotB.offer.price).toLocaleString('fa-IR')} تومان{' '}
                {slotA.offer.price < slotB.offer.price ? '(اولی ارزان‌تر است)' : '(دومی ارزان‌تر است)'}
              </dd>
            </div>
          </dl>
          <div style={{ textAlign: 'center', marginTop: 12 }}>
            <button
              type="button"
              className="fd-done"
              style={{ width: 'auto', padding: '6px 20px', borderRadius: 'var(--r-lg)' }}
              onClick={() => openModal('cmp', { slotA, slotB })}
            >
              مشاهده جدول مقایسه کامل
            </button>
          </div>
        </>
      ) : (
        <p className="cmp-hint">یک فروشگاه دیگر انتخاب کنید تا مقایسه کامل شود.</p>
      )}
    </section>
  );
};
