'use client';

import React from 'react';
import { useApp } from '../../context/AppContext';
import { ICONS, SvgIcon } from '../../data/icons';
import { STOCK_LABELS } from '../../data/mockData';

export const FilterModal: React.FC = () => {
  const { activeModal, closeModal, filters, setFilters, resetFilters } = useApp();

  if (activeModal !== 'filter') return null;

  return (
    <div className="modal-backdrop" onClick={closeModal}>
      <dialog className="fdlg" id="filterDlg" open onClick={(e) => e.stopPropagation()}>
        <header className="fd-head">
          <h2 id="fTitle">فیلتر</h2>
          <button type="button" className="icon-btn sm" id="fClose" onClick={closeModal} aria-label="بستن">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>

        <div className="fd-body" id="fBody">
          {/* موجودی */}
          <section className="fs">
            <h3>موجودی</h3>
            <div className="fcs">
              <button
                type="button"
                className={`chip ${!filters.inStockOnly ? 'on' : ''}`}
                onClick={() => setFilters((f) => ({ ...f, inStockOnly: false }))}
              >
                همه
              </button>
              <button
                type="button"
                className={`chip ${filters.inStockOnly ? 'on' : ''}`}
                onClick={() => setFilters((f) => ({ ...f, inStockOnly: true }))}
              >
                <span className="stock in">موجود و بروز</span>
              </button>
            </div>
          </section>

          {/* پرداخت */}
          <section className="fs">
            <h3>پرداخت</h3>
            <label className="frow">
              <input
                type="checkbox"
                checked={filters.torobpayOnly}
                onChange={(e) => setFilters((f) => ({ ...f, torobpayOnly: e.target.checked }))}
              />
              <span className="frow-t">
                <span dangerouslySetInnerHTML={{ __html: ICONS.torobpay }} />
                پرداخت با ترب‌پی فعال باشد
              </span>
            </label>

            <label className="frow">
              <input
                type="checkbox"
                checked={filters.installmentsOnly}
                onChange={(e) => setFilters((f) => ({ ...f, installmentsOnly: e.target.checked }))}
              />
              <span className="frow-t">
                <SvgIcon name="installment" size={16} />
                امکان پرداخت قسطی
              </span>
            </label>
          </section>

          {/* گارانتی و فروشگاه */}
          <section className="fs">
            <h3>فروشگاه و اعتبار</h3>
            <div className="fcs">
              {[0, 3.5, 4, 4.5].map((r) => (
                <button
                  key={r}
                  type="button"
                  className={`chip ${filters.minRating === r ? 'on' : ''}`}
                  onClick={() => setFilters((f) => ({ ...f, minRating: r }))}
                >
                  {r === 0 ? 'همهٔ امتیازها' : `امتیاز ★ ${r.toLocaleString('fa-IR')}+`}
                </button>
              ))}
            </div>

            <label className="frow">
              <input
                type="checkbox"
                checked={filters.guaranteeOnly}
                onChange={(e) => setFilters((f) => ({ ...f, guaranteeOnly: e.target.checked }))}
              />
              <span className="frow-t">فقط فروشگاه‌های دارای ضمانت ترب</span>
            </label>

            <label className="frow">
              <input
                type="checkbox"
                checked={filters.fastOnly}
                onChange={(e) => setFilters((f) => ({ ...f, fastOnly: e.target.checked }))}
              />
              <span className="frow-t">
                <SvgIcon name="truck" size={16} />
                ارسال فوری
              </span>
            </label>
          </section>

          {/* محدوده جستجو */}
          <section className="fs">
            <h3>محدودهٔ جستجو</h3>
            <div className="fcs">
              {[0, 2, 5, 10, 20].map((k) => (
                <button
                  key={k}
                  type="button"
                  className={`chip ${filters.maxDistance === (k === 0 ? 50 : k) ? 'on' : ''}`}
                  onClick={() => setFilters((f) => ({ ...f, maxDistance: k === 0 ? 50 : k }))}
                >
                  {k === 0 ? 'همه‌جا' : `تا ${k.toLocaleString('fa-IR')} کیلومتر`}
                </button>
              ))}
            </div>
          </section>

          {/* ساعت کار */}
          <section className="fs">
            <h3>ساعت کار</h3>
            <label className="frow">
              <input
                type="checkbox"
                checked={filters.openNowOnly}
                onChange={(e) => setFilters((f) => ({ ...f, openNowOnly: e.target.checked }))}
              />
              <span className="frow-t">فقط فروشگاه‌هایی که همین الان باز هستند</span>
            </label>
          </section>
        </div>

        <footer className="fd-foot">
          <button type="button" className="fd-reset" id="fReset" onClick={resetFilters}>
            حذف فیلترها
          </button>
          <button type="button" className="fd-done" id="fDone" onClick={closeModal}>
            نمایش نتایج
          </button>
        </footer>
      </dialog>
    </div>
  );
};
