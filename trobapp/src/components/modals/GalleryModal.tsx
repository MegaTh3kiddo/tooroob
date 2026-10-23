'use client';

import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Product } from '../../types';
import { getProductArt } from '../../data/art';
import { COLORS } from '../../data/mockData';

export const GalleryModal: React.FC = () => {
  const { activeModal, closeModal, modalData } = useApp();
  const [activeIdx, setActiveIdx] = useState(0);

  if (activeModal !== 'gallery' || !modalData) return null;
  const prod = modalData as Product;
  const colors = prod.colors || ['مشکی', 'سفید', 'سرمه‌ای'];

  const views = colors.map((c) => ({
    title: `رنگ ${c}`,
    html: getProductArt(prod.kind || 'over', COLORS[c] || '#8C9692'),
  }));

  const currentView = views[activeIdx] || views[0];

  return (
    <div className="modal-backdrop" onClick={closeModal}>
      <dialog className="gal" id="galDlg" open onClick={(e) => e.stopPropagation()}>
        <div className="gal-top">
          <span className="gal-title" id="galTitle">{prod.title}</span>
          <span className="gal-count" id="galCount">{(activeIdx + 1).toLocaleString('fa-IR')} از {views.length.toLocaleString('fa-IR')}</span>
          <button type="button" className="gal-x" id="galClose" onClick={closeModal} aria-label="بستن گالری">×</button>
        </div>

        <div className="gal-body">
          <button
            type="button"
            className="gal-nav prev"
            id="galPrev"
            aria-label="تصویر قبلی"
            onClick={() => setActiveIdx((prev) => (prev > 0 ? prev - 1 : views.length - 1))}
          >
            ›
          </button>

          <div
            className="gal-view"
            id="galView"
            dangerouslySetInnerHTML={{ __html: currentView.html }}
          />

          <button
            type="button"
            className="gal-nav next"
            id="galNext"
            aria-label="تصویر بعدی"
            onClick={() => setActiveIdx((prev) => (prev < views.length - 1 ? prev + 1 : 0))}
          >
            ‹
          </button>
        </div>

        <div className="gal-thumbs" id="galThumbs">
          {views.map((v, i) => (
            <button
              key={i}
              type="button"
              className={`gal-th ${i === activeIdx ? 'sel' : ''}`}
              onClick={() => setActiveIdx(i)}
              dangerouslySetInnerHTML={{ __html: v.html }}
            />
          ))}
        </div>
      </dialog>
    </div>
  );
};
