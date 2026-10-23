'use client';

import React from 'react';
import { useApp } from '../../context/AppContext';

export const CompareModal: React.FC = () => {
  const { activeModal, closeModal, modalData, openModal } = useApp();

  if (activeModal !== 'cmp' || !modalData) return null;
  const { slotA, slotB } = modalData;

  if (!slotA || !slotB) return null;

  return (
    <div className="modal-backdrop" onClick={closeModal}>
      <dialog className="fdlg cmpdlg" id="cmpDlg" open onClick={(e) => e.stopPropagation()}>
        <header className="fd-head">
          <h2 id="cmpDlgTitle">مقایسهٔ کامل دو فروشگاه</h2>
          <button type="button" className="icon-btn sm" id="cmpDlgClose" onClick={closeModal} aria-label="بستن">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>

        <div className="spec-body" id="cmpDlgBody">
          <div className="cgrid-wrap">
            <div className="cgrid sx-list" role="table" style={{ '--n': 2 } as any}>
              <div className="cg-row cg-head" role="row">
                <span className="cg-l" role="columnheader">ویژگی</span>
                <span className="cg-v" role="columnheader">{slotA.storeName}</span>
                <span className="cg-v" role="columnheader">{slotB.storeName}</span>
              </div>

              <div className="cg-row sx-row" role="row">
                <span className="cg-l">قیمت کالا</span>
                <span className="cg-v win">{slotA.offer.price.toLocaleString('fa-IR')} تومان</span>
                <span className="cg-v">{slotB.offer.price.toLocaleString('fa-IR')} تومان</span>
              </div>

              <div className="cg-row sx-row" role="row">
                <span className="cg-l">اختلاف قیمت</span>
                <span className="cg-v" style={{ gridColumn: 'span 2', textAlign: 'center' }}>
                  {Math.abs(slotA.offer.price - slotB.offer.price).toLocaleString('fa-IR')} تومان{' '}
                  {slotA.offer.price < slotB.offer.price ? `(${slotA.storeName} ارزان‌تر است)` : `(${slotB.storeName} ارزان‌تر است)`}
                </span>
              </div>

              <div className="cg-row sx-row" role="row">
                <span className="cg-l">ضمانت ترب</span>
                <span className="cg-v">{slotA.offer.store?.guarantee ? 'دارد ✓' : 'ندارد'}</span>
                <span className="cg-v">{slotB.offer.store?.guarantee ? 'دارد ✓' : 'ندارد'}</span>
              </div>

              <div className="cg-row sx-row" role="row">
                <span className="cg-l">ترب‌پی (۴ قسط)</span>
                <span className="cg-v">{slotA.offer.store?.torobpay ? 'فعال ✓' : 'غیرفعال'}</span>
                <span className="cg-v">{slotB.offer.store?.torobpay ? 'فعال ✓' : 'غیرفعال'}</span>
              </div>

              <div className="cg-row sx-row" role="row">
                <span className="cg-l">امتیاز فروشگاه</span>
                <span className="cg-v">★ {slotA.offer.store?.rating?.toLocaleString('fa-IR') || '۴.۲'}</span>
                <span className="cg-v">★ {slotB.offer.store?.rating?.toLocaleString('fa-IR') || '۴.۵'}</span>
              </div>

              <div className="cg-row sx-row" role="row">
                <span className="cg-l">اقدام</span>
                <span className="cg-v">
                  <button
                    type="button"
                    className="act-btn call"
                    onClick={() => {
                      closeModal();
                      openModal('call', slotA.offer.store);
                    }}
                  >
                    تماس
                  </button>
                </span>
                <span className="cg-v">
                  <button
                    type="button"
                    className="act-btn call"
                    onClick={() => {
                      closeModal();
                      openModal('call', slotB.offer.store);
                    }}
                  >
                    تماس
                  </button>
                </span>
              </div>
            </div>
          </div>
        </div>
      </dialog>
    </div>
  );
};
