'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { ICONS, SvgIcon } from '../../data/icons';
import { STORES, ORIGIN, PRODUCTS } from '../../data/mockData';
import { calculateSchedule } from '../../services/travelService';
import { getProductArt, getStoreArt } from '../../data/art';

export const AgentView: React.FC = () => {
  const {
    chatMessages,
    sendChatMessage,
    isHistOpen,
    setIsHistOpen,
    isVisitsOpen,
    setIsVisitsOpen,
    planStops,
    removePlanStop,
    setStopDone,
    movePlanStop,
    clearPlan,
    travelMode,
    setTravelMode,
    openModal,
    setSelectedStoreForMap,
    setView,
  } = useApp();

  const [inputVal, setInputVal] = useState('');
  const [loading, setLoading] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [chatMessages, loading]);

  const handleSend = async (text?: string) => {
    const q = text || inputVal.trim();
    if (!q || loading) return;
    setInputVal('');
    setLoading(true);
    try {
      await sendChatMessage(q);
    } finally {
      setLoading(false);
    }
  };

  const schedule = calculateSchedule(ORIGIN, planStops, travelMode);
  const hasMessages = chatMessages.length > 1;

  return (
    <section className={`agent ${!hasMessages ? 'is-empty' : ''}`} id="agent" aria-label="تربچت">
      {/* نوار کناری گفتگوهای قبلی (agHist) */}
      <aside className={`ag-hist ${isHistOpen ? 'is-open' : ''}`} id="agHist" aria-label="گفتگوهای قبلی">
        <div className="ag-hist-h">
          <span className="ag-brand">
            <img src="/img/torobchat.png" alt="" width="30" height="30" />
            <b>تربچت</b>
          </span>
          <button
            type="button"
            className="ag-htoggle"
            id="agHToggle"
            aria-expanded={isHistOpen}
            aria-controls="agHist"
            aria-label="بستن نوار کناری"
            title="بستن نوار کناری"
            onClick={() => setIsHistOpen(!isHistOpen)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3.5" y="4.5" width="17" height="15" rx="3" />
              <path d="M15 4.5v15" />
            </svg>
          </button>
          <button
            type="button"
            className="ag-hx"
            id="agHClose"
            aria-label="بستن فهرست گفتگوها"
            onClick={() => setIsHistOpen(false)}
          >
            ×
          </button>
        </div>

        <button
          type="button"
          className="ag-hnew"
          id="agHNew"
          title="گفت‌وگوی جدید"
          onClick={() => {
            // New conversation
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
            <path d="M12 5v14M5 12h14" />
          </svg>
          <span>گفت‌وگوی جدید</span>
        </button>

        <ul className="ag-hlist" id="agHList">
          <li className="ag-hitem active">
            <span className="ag-htitle">پیشنهاد خرید هدفون و بررسی قیمت</span>
            <small className="ag-htime">امروز</small>
          </li>
          <li className="ag-hitem">
            <span className="ag-htitle">مقایسه فروشگاه‌های بازار نارنج و بهار</span>
            <small className="ag-htime">دیروز</small>
          </li>
          <li className="ag-hitem">
            <span className="ag-htitle">استعلام خرید اقساطی با ترب‌پی</span>
            <small className="ag-htime">۳ روز پیش</small>
          </li>
        </ul>
      </aside>

      <div className="ag-scrim" id="agScrim" hidden={!isHistOpen} onClick={() => setIsHistOpen(false)}></div>

      {/* بخش مرکزی گفتگو (agMain) */}
      <div className="ag-main">
        {!hasMessages && (
          <div className="ag-hello">
            <img className="ag-logo" src="/img/torobchat.png" alt="" width="76" height="76" />
            <h2 className="ag-hi">چطور می‌تونم کمکت کنم؟</h2>
            <p className="ag-sub">
              می‌تونی بگی چه محصولی می‌خوای، چقدر بودجه داری، یا فروشگاه‌های نزدیک رو برات پیدا کنم.
            </p>
          </div>
        )}

        <div className="ag-log" id="agLog" role="log" aria-live="polite" ref={logRef}>
          {chatMessages.map((msg) => {
            const isBot = msg.sender === 'agent';
            return (
              <div key={msg.id} className={`ag-msg ${isBot ? 'bot' : 'user'}`}>
                {isBot && (
                  <span className="ag-av" aria-hidden="true">
                    <img src="/img/torobchat.png" alt="" width="26" height="26" />
                  </span>
                )}
                <div className="ag-b">
                  <p>{msg.text}</p>

                  {/* کارت‌های محصول یا فروشگاه ضمیمه شده */}
                  {msg.cards && msg.cards.length > 0 && (
                    <div className="ag-cards-wrap" style={{ marginTop: 12 }}>
                      {msg.cards.map((c, i) => {
                        if (c.type === 'product' && c.data) {
                          const artSvg = getProductArt(c.data.kind || 'over', '#8C9692');
                          return (
                            <article key={i} className="ag-prod">
                              <span
                                className="ag-p-img"
                                dangerouslySetInnerHTML={{ __html: artSvg }}
                              />
                              <div className="ag-p-b">
                                <b className="ag-p-name" title={c.data.title}>
                                  {c.data.title}
                                </b>
                                {c.data.tagline && <small>{c.data.tagline}</small>}
                              </div>
                              <p className="ag-c-price">
                                <small>از</small> <b>۳,۸۹۰,۰۰۰</b> تومان
                              </p>
                              <div className="ag-c-acts">
                                <button
                                  type="button"
                                  className="ag-pick"
                                  onClick={() => handleSend(`فروشگاه‌های ${c.data.title}`)}
                                >
                                  فروشگاه‌ها
                                </button>
                                <button
                                  type="button"
                                  className="ag-go"
                                  onClick={() => openModal('spec', c.data)}
                                >
                                  جزئیات
                                </button>
                              </div>
                            </article>
                          );
                        }
                        return null;
                      })}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="ag-msg bot">
              <span className="ag-av" aria-hidden="true">
                <img src="/img/torobchat.png" alt="" width="26" height="26" />
              </span>
              <div className="ag-b">
                <span className="ag-typing">در حال نوشتن پاسخ...</span>
              </div>
            </div>
          )}
        </div>

        {/* پایین صفحهٔ گفتگو (agFoot) */}
        <div className="ag-foot">
          <div className="ag-chips" id="agChips" role="group" aria-label="پیشنهادها">
            {['گوشی تا ۳۰ میلیون چی بخرم؟', 'نزدیک‌ترین فروشگاه با تخفیف کجاست؟', 'هدفون با نویز کنسلینگ عالی', 'خرید قسطی با ترب‌پی'].map((chip, idx) => (
              <button
                key={idx}
                type="button"
                className="ag-chip"
                onClick={() => handleSend(chip)}
              >
                {chip}
              </button>
            ))}
          </div>

          <form
            className="ag-input"
            id="agForm"
            autoComplete="off"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
          >
            <label className="sr" htmlFor="agQ">پیام شما به تربچت</label>
            <input
              id="agQ"
              type="text"
              placeholder="از تربچت بپرسید..."
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
            />
            <button
              className="ag-send"
              id="agSend"
              type="submit"
              aria-label="ارسال پیام"
              disabled={!inputVal.trim() || loading}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
              </svg>
            </button>
          </form>
          <p className="ag-disclaimer">تربچت ممکن است اشتباه کند؛ اطلاعات مهم را با فروشگاه بررسی کنید.</p>
        </div>
      </div>

      {/* سایدبار برنامهٔ سر زدن در تربچت (agSide) */}
      <aside className={`ag-side ${isVisitsOpen ? 'is-open' : ''}`} id="agSide" aria-label="سر زدن‌ها">
        <div className="ag-side-h">
          <b>سر زدن‌ها</b>
          <div className="ag-side-tools">
            <span className="ag-side-mode">
              {travelMode === 'walk' ? 'پیاده' : travelMode === 'transit' ? 'اتوبوس/مترو' : 'ماشین'}
            </span>
            <button
              type="button"
              className="ag-side-x"
              id="agSideClose"
              aria-label="بستن"
              onClick={() => setIsVisitsOpen(false)}
            >
              ×
            </button>
          </div>
        </div>

        <div className="ag-side-b">
          {planStops.length === 0 ? (
            <div className="as-empty">
              <p>فروشگاهی در برنامه نیست.</p>
              <span>برای سر زدن، روی دکمهٔ «سر زدن» در کارت فروشگاه‌ها کلیک کنید.</span>
            </div>
          ) : (
            <ul className="as-stops">
              {schedule.rows.map((row, idx) => {
                const sid = row.stop.sid;
                const store = STORES[sid];
                return (
                  <li key={sid} className={`as-stop ${row.stop.done ? 'is-done' : ''}`}>
                    <div className="as-stop-num">{idx + 1}</div>
                    <div className="as-stop-info">
                      <div className="as-stop-top">
                        <h4 className="as-stop-name">{row.storeName}</h4>
                        <span className={`as-status ${row.status}`}>
                          {row.status === 'open' ? 'باز' : row.status === 'soon' ? 'به‌زودی می‌بندد' : 'بسته'}
                        </span>
                      </div>
                      <p className="as-stop-addr">{store?.addr}</p>
                      <div className="as-stop-meta">
                        <span>{Number(row.km.toFixed(1)).toLocaleString('fa-IR')} کیلومتر</span> ·{' '}
                        <span>{row.travelMin.toLocaleString('fa-IR')} دقیقه فاصله</span>
                      </div>
                    </div>
                    <div className="as-stop-actions">
                      <button
                        type="button"
                        className="as-btn check"
                        onClick={() => setStopDone(sid, !row.stop.done)}
                      >
                        ✓
                      </button>
                      <button
                        type="button"
                        className="as-btn del"
                        onClick={() => removePlanStop(sid)}
                      >
                        ×
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </aside>
    </section>
  );
};
