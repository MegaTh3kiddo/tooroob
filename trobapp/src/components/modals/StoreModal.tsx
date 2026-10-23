'use client';

import React from 'react';
import { useApp } from '../../context/AppContext';
import { ICONS, SvgIcon } from '../../data/icons';
import { Store } from '../../types';
import { getStoreArt } from '../../data/art';
import { roadKm, travelMinutes, resolveMode } from '../../services/travelService';
import { ORIGIN } from '../../data/mockData';

export const StoreModal: React.FC = () => {
  const { activeModal, closeModal, modalData, openModal, togglePlanStop, planStops, travelMode, setView, setSelectedStoreForMap } = useApp();

  if (activeModal !== 'store' || !modalData) return null;
  const store = modalData as Store;
  const sid = store.id || 's1';
  const km = roadKm(ORIGIN, { lat: store.lat, lng: store.lng });
  const tm = travelMinutes(resolveMode(travelMode, km), km);
  const isPlanned = planStops.some((s) => s.sid === sid);

  const now = new Date();
  const currentH = now.getHours();
  const isOpen = currentH >= store.openH && currentH < store.closeH;

  return (
    <div className="modal-backdrop" onClick={closeModal}>
      <dialog className="fdlg storedlg" id="storeDlg" open onClick={(e) => e.stopPropagation()}>
        <header className="fd-head">
          <h2 id="storeDlgTitle">اطلاعات فروشگاه</h2>
          <button type="button" className="icon-btn sm" id="storeDlgClose" onClick={closeModal} aria-label="بستن">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>

        <div className="store-det" id="storeDlgBody">
          <div className="sd-top">
            <span
              className="sd-art"
              aria-hidden="true"
              dangerouslySetInnerHTML={{ __html: getStoreArt(sid) }}
            />
            <div className="sd-info">
              <div className="c-nm">
                {store.guarantee && (
                  <span className="torob-guarantee" role="link" tabIndex={-1}>
                    <span className="styles_hologram__5u9vV" style={{ width: 24, height: 24 }}>
                      <span className="styles_star__jo3q8"><span className="styles_wavyPattern__3a8qy"><span className="styles_wavyPatternLight__7Ymlp"></span></span></span>
                      <span className="styles_torobLogo__rNXpC"><span className="styles_torobLogoLight__xQOQ_"></span></span>
                    </span>
                  </span>
                )}
                {store.torobpay && (
                  <span className="pay tp" dangerouslySetInnerHTML={{ __html: ICONS.torobpay }} />
                )}
                <b className="sd-name">{store.name}</b>
              </div>

              <div className="c-var">
                <span>فروشگاه کالای دیجیتال</span> ·{' '}
                {store.rating && (
                  <span className="rate">
                    <SvgIcon name="star" size={14} />
                    <b>{store.rating.toLocaleString('fa-IR', { minimumFractionDigits: 1 })}</b>
                    <small>({store.years.toLocaleString('fa-IR')} سال در ترب)</small>
                  </span>
                )}
              </div>

              <div className="c-meta">
                <span className={`status ${isOpen ? 'open' : 'closed'}`}>{isOpen ? 'باز است' : 'بسته'}</span>
                <span>{Number(km.toFixed(1)).toLocaleString('fa-IR')} کیلومتر</span>
                <span className="eta">
                  <SvgIcon name="car" size={14} />
                  <span>{tm.toLocaleString('fa-IR')} دقیقه</span>
                </span>
              </div>

              <button
                type="button"
                className="sd-guide"
                data-guide={sid}
                onClick={() => {
                  closeModal();
                  setSelectedStoreForMap(sid);
                  setView('map');
                }}
              >
                <SvgIcon name="route" size={16} />
                <span>راهنمای رسیدن به فروشگاه</span>
              </button>
            </div>
          </div>

          <dl className="det">
            <dt>نشانی</dt>
            <dd>{store.addr}</dd>

            <dt>ساعت کار</dt>
            <dd>{store.hours}</dd>

            <dt>تلفن</dt>
            <dd className="tels">
              {(store.phones || [store.phone]).map((p, idx) => (
                <React.Fragment key={p}>
                  <a className="tel" href={`tel:${p.replace(/[^0-9]/g, '')}`} dir="ltr">
                    {p}
                  </a>
                  {idx < (store.phones || []).length - 1 && <i className="rsep">·</i>}
                </React.Fragment>
              ))}
            </dd>

            {store.fast && (
              <>
                <dt>ارسال</dt>
                <dd className="fastv">
                  <SvgIcon name="truck" size={14} />
                  {store.fast}
                </dd>
              </>
            )}

            <dd className="wide-row">
              <div className="acts">
                <button
                  type="button"
                  className="act-btn call"
                  onClick={() => {
                    closeModal();
                    openModal('call', store);
                  }}
                >
                  <SvgIcon name="phone" size={16} />
                  <span>تماس</span>
                </button>

                <button
                  type="button"
                  className={`act-btn plan ${isPlanned ? 'saved' : ''}`}
                  onClick={() => togglePlanStop(sid)}
                >
                  <SvgIcon name="bookmark" size={16} />
                  <span>{isPlanned ? 'در سر زدن‌ها' : 'افزودن به سر زدن‌ها'}</span>
                </button>

                <button
                  type="button"
                  className="act-btn route"
                  onClick={() => {
                    closeModal();
                    setSelectedStoreForMap(sid);
                    setView('map');
                  }}
                >
                  <SvgIcon name="route" size={16} />
                  <span>روی نقشه</span>
                </button>
              </div>
            </dd>

            <dd className="wide-row det-foot">
              <button
                type="button"
                className="report-btn"
                onClick={() => {
                  closeModal();
                  openModal('report', store);
                }}
              >
                <SvgIcon name="flag" size={14} />
                <span>گزارش مشکل فروشگاه</span>
              </button>
            </dd>
          </dl>
        </div>
      </dialog>
    </div>
  );
};
