'use client';

import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { ICONS, SvgIcon } from '../../data/icons';
import { STORES } from '../../data/mockData';
import { getStoreArt } from '../../data/art';

export const InquiriesView: React.FC = () => {
  const { inquiries, openModal, togglePlanStop, planStops, setSelectedStoreForMap, setView } = useApp();
  const [filterMode, setFilterMode] = useState<'all' | 'pending' | 'answered' | 'noreply'>('all');

  const counts = {
    all: inquiries.length,
    pending: inquiries.filter((q) => q.status === 'pending').length,
    answered: inquiries.filter((q) => q.status === 'answered').length,
    noreply: inquiries.filter((q) => q.status === 'expired' || q.status === 'canceled').length,
  };

  const filteredInquiries = inquiries.filter((q) => {
    if (filterMode === 'all') return true;
    if (filterMode === 'noreply') return q.status === 'expired' || q.status === 'canceled';
    return q.status === filterMode;
  });

  return (
    <section className="inqs" id="inqs" aria-labelledby="iqTitle">
      <header className="iq-head">
        <h2 id="iqTitle">استعلام‌های من</h2>
        <p>قیمت و موجودی‌ای که ترب از فروشنده‌ها برایتان پرسیده. جواب هر استعلام که برسد خبرتان می‌کنیم.</p>
      </header>

      <div className="seg iq-seg" id="iqSeg" role="radiogroup" aria-label="وضعیت استعلام">
        <button
          type="button"
          role="radio"
          data-iq="all"
          aria-checked={filterMode === 'all'}
          onClick={() => setFilterMode('all')}
        >
          همه <small>{counts.all.toLocaleString('fa-IR')}</small>
        </button>
        <button
          type="button"
          role="radio"
          data-iq="pending"
          aria-checked={filterMode === 'pending'}
          onClick={() => setFilterMode('pending')}
        >
          در انتظار <small>{counts.pending.toLocaleString('fa-IR')}</small>
        </button>
        <button
          type="button"
          role="radio"
          data-iq="answered"
          aria-checked={filterMode === 'answered'}
          onClick={() => setFilterMode('answered')}
        >
          پاسخ داده‌شده <small>{counts.answered.toLocaleString('fa-IR')}</small>
        </button>
        <button
          type="button"
          role="radio"
          data-iq="noreply"
          aria-checked={filterMode === 'noreply'}
          onClick={() => setFilterMode('noreply')}
        >
          بدون پاسخ <small>{counts.noreply.toLocaleString('fa-IR')}</small>
        </button>
      </div>

      <ul className="iq-list" id="iqList">
        {filteredInquiries.length === 0 ? (
          <li className="empty">
            {inquiries.length
              ? 'استعلامی در این دسته نیست.'
              : 'هنوز استعلامی نگرفته‌اید. در اطلاعات هر فروشگاه «استعلام قیمت» را بزنید.'}
          </li>
        ) : (
          filteredInquiries.map((q) => {
            const store = STORES[q.shop_id];
            const isPlanned = planStops.some((s) => s.sid === q.shop_id);
            const a = q.answer;

            return (
              <li key={q.id} className={`iq-card st-${q.status}`}>
                <div className="iq-top">
                  <span
                    className="iq-art"
                    aria-hidden="true"
                    dangerouslySetInnerHTML={{ __html: getStoreArt(q.shop_id) }}
                  />
                  <button
                    type="button"
                    className="iq-t"
                    data-iq-store={q.id}
                    onClick={() => {
                      if (store) openModal('store', store);
                    }}
                  >
                    <b>{q.shop_name}</b>
                    <small>{q.product_title || 'استعلام قیمت کالا'}</small>
                  </button>

                  <span className={`iq-badge ${q.status === 'answered' ? 'answered' : q.status === 'pending' ? 'wait' : 'expired'}`}>
                    {q.status === 'answered'
                      ? 'پاسخ داده‌شده'
                      : q.status === 'pending'
                      ? 'در انتظار پاسخ'
                      : 'بدون پاسخ'}
                  </span>
                </div>

                {q.status === 'answered' && a ? (
                  <div className="iq-ans">
                    <div className="iq-price">
                      <span>قیمت اعلام‌شده</span>
                      <b>{a.confirmed_price?.toLocaleString('fa-IR')} <small>تومان</small></b>
                    </div>
                    <span className={`stock ${a.in_stock ? 'in' : 'out'}`}>
                      {a.in_stock ? 'موجود است' : 'فعلاً موجود نیست'}
                    </span>
                    {a.notes && (
                      <p className="iq-note">
                        «{a.notes}» <small>— فروشنده، ۱ ساعت پیش</small>
                      </p>
                    )}
                    <p className="iq-valid">این پاسخ تا ۲ ساعت دیگر معتبر است.</p>
                  </div>
                ) : (
                  <div className="iq-wait">
                    <i className="iq-bar"></i>
                    <span>ترب در حال پرسیدن از فروشنده است؛ معمولاً تا ۲۰ دقیقه.</span>
                  </div>
                )}

                <div className="iq-foot">
                  <span className="iq-time">ثبت ۱ ساعت پیش · نمونه</span>
                  <div className="iq-acts">
                    {store && (
                      <button
                        type="button"
                        className="act wa"
                        data-call={q.shop_id}
                        aria-label="تماس با فروشگاه"
                        data-hint="تماس با فروشگاه"
                        onClick={() => openModal('call', store)}
                        dangerouslySetInnerHTML={{ __html: ICONS.phone }}
                      />
                    )}

                    <button
                      type="button"
                      className="act wa"
                      data-iq-map={q.id}
                      aria-label="روی نقشه"
                      data-hint="روی نقشه"
                      onClick={() => {
                        setSelectedStoreForMap(q.shop_id);
                        setView('map');
                      }}
                      dangerouslySetInnerHTML={{ __html: ICONS.map }}
                    />

                    <button
                      type="button"
                      className="act wa"
                      data-iq-plan={q.id}
                      aria-pressed={isPlanned}
                      aria-label="سر زدن"
                      data-hint={isPlanned ? 'در سر زدن‌ها' : 'افزودن به سر زدن‌ها'}
                      onClick={() => togglePlanStop(q.shop_id)}
                      dangerouslySetInnerHTML={{ __html: ICONS.bookmark }}
                    />

                    <button
                      type="button"
                      className="act wa"
                      data-iq-rm={q.id}
                      aria-label="حذف استعلام"
                      data-hint="حذف"
                      onClick={() => {
                        // remove
                      }}
                      dangerouslySetInnerHTML={{ __html: ICONS.x }}
                    />
                  </div>
                </div>
              </li>
            );
          })
        )}
      </ul>
    </section>
  );
};
