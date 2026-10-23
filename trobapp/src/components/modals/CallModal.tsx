'use client';

import React from 'react';
import { useApp } from '../../context/AppContext';
import { ICONS, SvgIcon } from '../../data/icons';
import { Store } from '../../types';

export const CallModal: React.FC = () => {
  const { activeModal, closeModal, modalData } = useApp();

  if (activeModal !== 'call' || !modalData) return null;
  const store = modalData as Store;
  const phones = store.phones && store.phones.length > 0 ? store.phones : [store.phone];

  return (
    <div className="modal-backdrop" onClick={closeModal}>
      <dialog className="fdlg calldlg" id="callDlg" open onClick={(e) => e.stopPropagation()}>
        <header className="fd-head">
          <div className="call-h">
            <h2 id="callTitle">با کدام شماره تماس می‌گیرید؟</h2>
            <p id="callStore">{store.name}</p>
          </div>
          <button type="button" className="icon-btn sm" id="callClose" onClick={closeModal} aria-label="بستن">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>

        <ul className="call-list" id="callList">
          {phones.map((p) => {
            const isMobile = p.startsWith('۰۹') || p.startsWith('09');
            const telHref = `tel:${p.replace(/[^0-9]/g, '')}`;
            return (
              <a key={p} className="call-opt" href={telHref}>
                <span className="co-ic" dangerouslySetInnerHTML={{ __html: ICONS.phone }} />
                <span className="co-t">
                  <b dir="ltr">{p}</b>
                  <small>{isMobile ? 'همراه' : 'ثابت'}</small>
                </span>
                <span className="co-go">تماس</span>
              </a>
            );
          })}
        </ul>
        <div className="call-all" id="callAll" hidden></div>
      </dialog>
    </div>
  );
};
