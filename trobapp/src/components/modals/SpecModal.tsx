'use client';

import React from 'react';
import { useApp } from '../../context/AppContext';
import { Product } from '../../types';
import { getProductArt } from '../../data/art';
import { COLORS } from '../../data/mockData';

export const SpecModal: React.FC = () => {
  const { activeModal, closeModal, modalData } = useApp();

  if (activeModal !== 'spec' || !modalData) return null;
  const prod = modalData as Product;
  const artSvg = getProductArt(prod.kind || 'over', COLORS[prod.colors?.[0] || 'مشکی']);

  return (
    <div className="modal-backdrop" onClick={closeModal}>
      <dialog className="fdlg specdlg" id="specDlg" open onClick={(e) => e.stopPropagation()}>
        <header className="fd-head">
          <h2 id="specTitle">مشخصات کامل</h2>
          <button type="button" className="icon-btn sm" id="specClose" onClick={closeModal} aria-label="بستن">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>

        <div className="spec-body" id="specBody">
          <div className="sx-prod">
            <span className="sx-img" dangerouslySetInnerHTML={{ __html: artSvg }} />
            <div className="sx-pi">
              <b>{prod.title}</b>
              {prod.tagline && <small>{prod.tagline}</small>}
            </div>
          </div>

          <div className="sx-list">
            <section className="sx-group">
              <h3 className="sx-head">مشخصات کلیدی <small>({(prod.specs?.length || 0).toLocaleString('fa-IR')})</small></h3>
              {prod.specs &&
                prod.specs.map(([k, v], idx) => (
                  <div key={idx} className="sx-row">
                    <span className="sx-k">{k}</span>
                    <span className="sx-v">{v}</span>
                  </div>
                ))}
              {prod.more &&
                prod.more.map(([k, v], idx) => (
                  <div key={`m_${idx}`} className="sx-row">
                    <span className="sx-k">{k}</span>
                    <span className="sx-v">{v}</span>
                  </div>
                ))}
            </section>
          </div>
          <p className="sp-note">مشخصات نمونه است و برای بررسی آورده شده است.</p>
        </div>
      </dialog>
    </div>
  );
};
