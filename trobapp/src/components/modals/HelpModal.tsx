'use client';

import React from 'react';
import { useApp } from '../../context/AppContext';
import { ICONS, SvgIcon } from '../../data/icons';

export const HelpModal: React.FC = () => {
  const { activeModal, closeModal } = useApp();

  if (activeModal !== 'help') return null;

  return (
    <div className="modal-backdrop" onClick={closeModal}>
      <dialog className="fdlg helpdlg" id="helpDlg" open onClick={(e) => e.stopPropagation()}>
        <header className="fd-head">
          <h2 id="helpTitle">
            <span className="h-logo" id="helpLogo" dangerouslySetInnerHTML={{ __html: ICONS.torob }} />
            راهنمای ترب
          </h2>
          <button type="button" className="icon-btn sm" id="helpClose" onClick={closeModal} aria-label="بستن">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>

        <div className="help-body" id="helpBody">
          <ul className="help-list">
            <li>
              <span className="h-ic">
                <span className="torob-guarantee" role="link" tabIndex={-1}>
                  <span className="styles_hologram__5u9vV" style={{ width: 24, height: 24 }}>
                    <span className="styles_star__jo3q8"><span className="styles_wavyPattern__3a8qy"><span className="styles_wavyPatternLight__7Ymlp"></span></span></span>
                    <span className="styles_torobLogo__rNXpC"><span className="styles_torobLogoLight__xQOQ_"></span></span>
                  </span>
                </span>
              </span>
              <span>
                <b>ضمانت ترب</b>
                اگر خرید از فروشگاهی که این نشان را دارد به مشکل بخورد (کالا با توضیحات یکی نباشد یا تحویل داده نشود)، ترب پیگیری می‌کند.
              </span>
            </li>

            <li>
              <span className="h-ic" dangerouslySetInnerHTML={{ __html: ICONS.torobpay }} />
              <span>
                <b>ترب‌پی</b>
                خرید قسطی؛ پرداخت در ۴ قسط بدون کارمزد. فروشگاه‌هایی که ترب‌پی دارند ضمانت ترب هم دارند، برای همین کنار نامشان فقط آیکون ترب‌پی می‌آید.
              </span>
            </li>

            <li>
              <span className="h-ic">
                <span className="pay ins">
                  <SvgIcon name="installment" size={16} />
                </span>
              </span>
              <span>
                <b>خرید اقساطی</b>
                فروشگاه روش‌های دیگری برای خرید قسطی هم دارد. در اطلاعات فروشگاه روی «پرداخت قسطی» بزنید تا همه را ببینید.
              </span>
            </li>

            <li>
              <span className="h-ic">
                <span className="rate">
                  <SvgIcon name="star" size={14} />
                  <b>۴٫۶</b>
                </span>
              </span>
              <span>
                <b>امتیاز فروشگاه</b>
                امتیاز ۱ تا ۵ و مدت حضور فروشگاه در ترب. در اطلاعات فروشگاه روی امتیاز بزنید تا جزئیات ارزیابی را ببینید.
              </span>
            </li>
          </ul>

          <a className="help-link" href="https://torob.com/pages/safe-shopping/" target="_blank" rel="noopener">
            <SvgIcon name="info" size={16} />
            <span>راهنمای خرید امن ترب</span>
          </a>
        </div>
      </dialog>
    </div>
  );
};
