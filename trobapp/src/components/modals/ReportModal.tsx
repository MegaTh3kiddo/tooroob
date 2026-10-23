'use client';

import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Store } from '../../types';
import { TorobApi } from '../../services/api';

const REPORT_REASONS = [
  'قیمت اشتباه',
  'ناموجود',
  'محصول متفاوت',
  'فریب در فروش',
  'پیگیری بعد از خرید',
  'اطلاعات یا هزینه ارسال اشتباه',
  'تفاوت قیمت سایت و ترب',
  'سایر',
];

export const ReportModal: React.FC = () => {
  const { activeModal, closeModal, modalData } = useApp();
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [note, setNote] = useState('');
  const [loading, setLoading] = useState(false);

  if (activeModal !== 'report' || !modalData) return null;
  const store = modalData as Store;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedIdx === null || loading) return;
    setLoading(true);
    try {
      await TorobApi.submitFeedback(store.id || 's1', REPORT_REASONS[selectedIdx], note);
      closeModal();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={closeModal}>
      <dialog className="fdlg reportdlg" id="reportDlg" open onClick={(e) => e.stopPropagation()}>
        <header className="fd-head">
          <div className="call-h">
            <h2 id="repTitle">گزارش فروشگاه</h2>
            <p id="repStore">{store.name}</p>
          </div>
          <button type="button" className="icon-btn sm" id="repClose" onClick={closeModal} aria-label="بستن">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>

        <form className="rep-form" id="repForm" onSubmit={handleSubmit}>
          <fieldset className="rep-opts">
            <legend>به چه مشکلی برخوردید؟</legend>
            <div id="repOpts">
              {REPORT_REASONS.map((r, i) => (
                <label key={i} className="rep-opt">
                  <input
                    type="radio"
                    name="repReason"
                    value={i}
                    checked={selectedIdx === i}
                    onChange={() => setSelectedIdx(i)}
                  />
                  <span>{r}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="rep-more">
            <label className="rep-lbl" htmlFor="repNote">
              توضیح بیشتر <small>(اختیاری)</small>
            </label>
            <textarea
              id="repNote"
              rows={3}
              placeholder="مثلاً: گفتند با این قیمت فقط نقد می‌فروشند..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>

          <footer className="rep-foot">
            <button type="button" className="fd-reset" id="repCancel" onClick={closeModal}>
              انصراف
            </button>
            <button
              type="submit"
              className="fd-done"
              id="repSend"
              disabled={selectedIdx === null || loading}
            >
              {loading ? 'در حال ثبت...' : 'ثبت گزارش'}
            </button>
          </footer>
        </form>
      </dialog>
    </div>
  );
};
