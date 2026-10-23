'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { CATS } from '../../data/mockData';
import { ICONS } from '../../data/icons';

export const Header: React.FC = () => {
  const {
    view,
    setView,
    city,
    setCity,
    cities,
    searchQuery,
    setSearchQuery,
    activeCategory,
    setActiveCategory,
    planStops,
    inquiries,
    isTopCollapsed,
    setIsTopCollapsed,
    isVisitsOpen,
    setIsVisitsOpen,
    isHistOpen,
    setIsHistOpen,
    openModal,
    clearChat,
    theme,
    toggleTheme,
    user,
    logout,
  } = useApp();

  const [cityOpen, setCityOpen] = useState(false);
  const [citySearch, setCitySearch] = useState('');
  const [acctMenuOpen, setAcctMenuOpen] = useState(false);
  const cityPopRef = useRef<HTMLDivElement>(null);
  const acctRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (cityPopRef.current && !cityPopRef.current.contains(e.target as Node)) {
        setCityOpen(false);
      }
      if (acctRef.current && !acctRef.current.contains(e.target as Node)) {
        setAcctMenuOpen(false);
      }
    }
    if (cityOpen || acctMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [cityOpen, acctMenuOpen]);

  const filteredCities = cities.filter((c) =>
    c.name.toLowerCase().includes(citySearch.toLowerCase())
  );

  const activeInquiriesCount = inquiries.filter((i) => !i.answer || i.status === 'answered').length;

  return (
    <header className="top">
      <div className="brand">
        {/* تربچت: باز کردن فهرست گفتگوهای قبلی */}
        <button
          className="icon-btn ag-only hist-btn"
          id="histBtn"
          type="button"
          aria-controls="agHist"
          aria-expanded={isHistOpen}
          aria-label="گفتگوهای قبلی"
          title="گفتگوهای قبلی"
          onClick={() => setIsHistOpen(!isHistOpen)}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>

        <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
          <rect className="logo-bg" width="32" height="32" rx="9" />
          <g className="logo-torob" transform="translate(6.3 6.3) scale(.22)">
            <path d="M79.245 20.322l-.627.726c-2.474 2.656-5.814 4.2-9.462 4.313-.16.023-.342.023-.502.023-.456 0-.878-.023-1.31-.068 8.595 10.1 9.895 24.968 2.222 36.579-7.638 11.542-21.774 16.252-34.428 12.484h-.08c-5.13-1.34-10.944.68-14.022 5.414 3.192-4.847 2.736-11.055-.798-15.322v-.045c-8.333-10.079-9.473-24.72-1.870-36.160C26.692 15.670 42.766 11.220 56.195 17.031c-.57-1.476-.935-3.065-1.026-4.688-.114-2.95.741-5.788 2.371-8.171-18.012-5.902-38.532.567-49.476 17.137C-5.104 41.171.425 67.842 20.261 80.893c19.882 13.064 46.592 7.502 59.702-12.246 10.032-15.174 9.177-34.331-.707-48.348l-.011.023z" />
            <path d="M31.969 10.22c-10.91 1.08-20.463 5.721-24.054 11.191C-5.195 41.216.3 67.853 20.193 80.905l.73-1.112c3.191-4.847 2.735-11.055-.799-15.322v-.045c-8.22-10.079-9.36-24.72-1.835-36.16C26.61 15.67 42.685 11.22 56.114 17.031c0 0-11.4-8.059-24.122-6.81h-.023z" />
            <path d="M62.544 22.32s-.342-4.086 1.482-7.037c1.824-2.951 5.7-5.845 10.602-5.539 4.925.307 5.723 1.442 5.723 1.442s.114 3.972-1.254 6.242-4.218 5.606-8.322 6.446c-4.104.829-8.231-1.555-8.231-1.555z" />
            <path d="M61.062 21.173s-.456-3.972 2.28-7.944c2.736-3.973 5.7-4.563 5.7-4.563S68.7 3.218 66.078.608c.228-.057-3.124.08-6.042 3.291-2.577 2.815-4.104 7.264-2.964 11.577 1.14 4.312 3.99 5.697 3.99 5.697z" />
          </g>
        </svg>

        <h1 className="brand-name">ترب مپ</h1>

        {/* انتخاب شهر */}
        <div className="city" id="city" ref={cityPopRef}>
          <button
            className="city-btn"
            id="cityBtn"
            type="button"
            aria-haspopup="listbox"
            aria-expanded={cityOpen}
            aria-controls="cityPop"
            onClick={() => setCityOpen(!cityOpen)}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z" />
              <circle cx="12" cy="10" r="2.3" />
            </svg>
            <span id="cityName">{city.name}</span>
            <svg className="city-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>

          <div className="city-pop" id="cityPop" hidden={!cityOpen}>
            <label className="sr" htmlFor="cityQ">جستجوی شهر</label>
            <div className="city-search">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-3.6-3.6" />
              </svg>
              <input
                id="cityQ"
                type="text"
                autoComplete="off"
                placeholder="نام شهر را بنویسید"
                role="combobox"
                aria-expanded={cityOpen}
                aria-controls="cityList"
                value={citySearch}
                onChange={(e) => setCitySearch(e.target.value)}
              />
            </div>
            <ul className="city-list" id="cityList" role="listbox" aria-label="شهرها">
              {filteredCities.map((c) => (
                <li
                  key={c.id}
                  className={`city-opt ${c.id === city.id ? 'sel' : ''} ${!c.active ? 'disabled' : ''}`}
                  role="option"
                  aria-selected={c.id === city.id}
                  onClick={() => {
                    if (c.active) {
                      setCity(c);
                      setCityOpen(false);
                    }
                  }}
                >
                  <span>{c.name}</span>
                  {!c.active && <span className="city-tag">به‌زودی</span>}
                </li>
              ))}
            </ul>
            <p className="city-note">نسخهٔ آزمایشی؛ فعلاً فقط تهران فعال است.</p>
          </div>
        </div>

        <div className="brand-tools">
          {/* جمع کردن بخش بالا */}
          <button
            className="icon-btn min-btn"
            id="minBtn"
            type="button"
            aria-expanded={!isTopCollapsed}
            aria-controls="searchForm"
            aria-label="جمع کردن بخش بالا"
            title="جمع کردن بخش بالا"
            onClick={() => setIsTopCollapsed(!isTopCollapsed)}
          >
            <svg className="i-up" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M7 11l5-5 5 5M7 18l5-5 5 5" />
            </svg>
            <svg className="i-down" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M7 6l5 5 5-5M7 13l5 5 5-5" />
            </svg>
          </button>

          {/* سر زدن‌ها */}
          <button
            className="icon-btn ag-only visits-btn"
            id="visitsBtn"
            type="button"
            aria-controls="agSide"
            aria-expanded={isVisitsOpen}
            aria-label="سر زدن‌ها"
            title="سر زدن‌ها"
            onClick={() => setIsVisitsOpen(!isVisitsOpen)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z" />
            </svg>
            <b className="vb-cnt" id="visitsCnt" hidden={planStops.length === 0}>
              {planStops.length.toLocaleString('fa-IR')}
            </b>
          </button>

          {/* گفتگوی تازه */}
          <button
            className="icon-btn ag-only"
            id="newChatBtn"
            type="button"
            aria-label="گفتگوی تازه"
            title="گفتگوی تازه"
            onClick={clearChat}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
              <path d="M12 5v14M5 12h14" />
            </svg>
          </button>

          {/* حساب کاربری */}
          <div className="acct" id="acct" ref={acctRef}>
            <button
              className="acct-btn"
              id="acctBtn"
              type="button"
              aria-haspopup="menu"
              aria-expanded={acctMenuOpen}
              aria-controls="acctMenu"
              aria-label={user.isLoggedIn ? 'حساب کاربری: کاربر ترب' : 'ورود به حساب'}
              onClick={() => setAcctMenuOpen(!acctMenuOpen)}
            >
              {user.isLoggedIn ? (
                <span className="acct-av">ک</span>
              ) : (
                <span className="acct-av off">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <circle cx="12" cy="8.5" r="3.8" />
                    <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
                  </svg>
                </span>
              )}
            </button>
            <div className="acct-menu" id="acctMenu" role="menu" hidden={!acctMenuOpen}>
              {user.isLoggedIn ? (
                <>
                  <div className="am-head">
                    <span className="acct-av lg">ک</span>
                    <div className="am-who">
                      <b>کاربر ترب</b>
                      <small dir="ltr">{user.phone || '۰۹۱۲۱۲۳۴۵۶۷'}</small>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="am-item"
                    role="menuitem"
                    onClick={() => {
                      setAcctMenuOpen(false);
                      openModal('account', { tab: 'profile' });
                    }}
                  >
                    <svg className="ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <circle cx="12" cy="8.5" r="3.8" />
                      <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
                    </svg>
                    <span>پروفایل</span>
                  </button>
                  <button
                    type="button"
                    className="am-item"
                    role="menuitem"
                    onClick={() => {
                      setAcctMenuOpen(false);
                      openModal('account', { tab: 'settings' });
                    }}
                  >
                    <svg className="ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <circle cx="12" cy="12" r="3" />
                      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
                    </svg>
                    <span>تنظیمات</span>
                  </button>
                  <button
                    type="button"
                    className="am-item"
                    role="menuitem"
                    onClick={() => {
                      setAcctMenuOpen(false);
                      openModal('account', { tab: 'sub' });
                    }}
                  >
                    <svg className="ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M3.5 8l4.5 4 4-6 4 6 4.5-4-2 10.5h-13z" />
                    </svg>
                    <span>اشتراک</span>
                    <em className="am-tag">رایگان</em>
                  </button>
                  <button
                    type="button"
                    className="am-item"
                    role="menuitem"
                    onClick={() => {
                      setAcctMenuOpen(false);
                      openModal('account', { tab: 'support' });
                    }}
                  >
                    <svg className="ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M20 12a8 8 0 0 1-11.6 7.1L4 20l1-4.2A8 8 0 1 1 20 12z" />
                      <path d="M8.5 11h7M8.5 14h4" />
                    </svg>
                    <span>بازخورد و پشتیبانی</span>
                  </button>
                  <div className="am-seg" role="group" aria-label="حالت نمایش">
                    <button
                      type="button"
                      data-theme-set="light"
                      aria-pressed={theme === 'light'}
                      onClick={() => {
                        if (theme !== 'light') toggleTheme();
                      }}
                    >
                      <svg className="ic" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <circle cx="12" cy="12" r="4" />
                        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
                      </svg>
                      <span>روشن</span>
                    </button>
                    <button
                      type="button"
                      data-theme-set="dark"
                      aria-pressed={theme === 'dark'}
                      onClick={() => {
                        if (theme !== 'dark') toggleTheme();
                      }}
                    >
                      <svg className="ic" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
                      </svg>
                      <span>تاریک</span>
                    </button>
                    <button type="button" data-theme-set="system" aria-pressed={false}>
                      <svg className="ic" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <circle cx="12" cy="12" r="8.5" />
                        <path d="M12 3.5v17a8.5 8.5 0 0 0 0-17z" fill="currentColor" />
                      </svg>
                      <span>خودکار</span>
                    </button>
                  </div>
                  <hr className="am-sep" />
                  <button
                    type="button"
                    className="am-item danger"
                    role="menuitem"
                    onClick={() => {
                      setAcctMenuOpen(false);
                      logout();
                    }}
                  >
                    <svg className="ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" />
                      <path d="M10 16l-4-4 4-4M6 12h10" />
                    </svg>
                    <span>خروج</span>
                  </button>
                </>
              ) : (
                <>
                  <div className="am-head">
                    <span className="acct-av lg off">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <circle cx="12" cy="8.5" r="3.8" />
                        <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
                      </svg>
                    </span>
                    <div className="am-who">
                      <b>وارد نشده‌ای</b>
                      <small>برای ذخیرهٔ گفتگوها و برنامه وارد شو</small>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="am-login"
                    role="menuitem"
                    onClick={() => {
                      setAcctMenuOpen(false);
                      openModal('account', { tab: 'login' });
                    }}
                  >
                    <svg className="ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3" />
                      <path d="M14 16l4-4-4-4M18 12H8" />
                    </svg>
                    <span>ورود به حساب</span>
                  </button>
                  <button
                    type="button"
                    className="am-item"
                    role="menuitem"
                    onClick={() => {
                      setAcctMenuOpen(false);
                      openModal('account', { tab: 'settings' });
                    }}
                  >
                    <svg className="ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <circle cx="12" cy="12" r="3" />
                      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
                    </svg>
                    <span>تنظیمات</span>
                  </button>
                  <button
                    type="button"
                    className="am-item"
                    role="menuitem"
                    onClick={() => {
                      setAcctMenuOpen(false);
                      openModal('account', { tab: 'support' });
                    }}
                  >
                    <svg className="ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M20 12a8 8 0 0 1-11.6 7.1L4 20l1-4.2A8 8 0 1 1 20 12z" />
                      <path d="M8.5 11h7M8.5 14h4" />
                    </svg>
                    <span>بازخورد و پشتیبانی</span>
                  </button>
                  <div className="am-seg" role="group" aria-label="حالت نمایش">
                    <button
                      type="button"
                      data-theme-set="light"
                      aria-pressed={theme === 'light'}
                      onClick={() => {
                        if (theme !== 'light') toggleTheme();
                      }}
                    >
                      <svg className="ic" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <circle cx="12" cy="12" r="4" />
                        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
                      </svg>
                      <span>روشن</span>
                    </button>
                    <button
                      type="button"
                      data-theme-set="dark"
                      aria-pressed={theme === 'dark'}
                      onClick={() => {
                        if (theme !== 'dark') toggleTheme();
                      }}
                    >
                      <svg className="ic" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
                      </svg>
                      <span>تاریک</span>
                    </button>
                    <button type="button" data-theme-set="system" aria-pressed={false}>
                      <svg className="ic" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <circle cx="12" cy="12" r="8.5" />
                        <path d="M12 3.5v17a8.5 8.5 0 0 0 0-17z" fill="currentColor" />
                      </svg>
                      <span>خودکار</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* تب‌های اصلی */}
      <nav className="views" id="views" aria-label="صفحه‌ها">
        <a
          className={`view-tab ${view === 'agent' ? 'active' : ''}`}
          href="#agent"
          data-view="agent"
          aria-current={view === 'agent' ? 'page' : undefined}
          onClick={(e) => {
            e.preventDefault();
            setView('agent');
          }}
        >
          <span className="vt-ic">
            <img className="vt-chat" src="/img/torobchat.png" alt="" width="22" height="22" />
          </span>
          <span>تربچت</span>
        </a>

        <a
          className={`view-tab ${view === 'list' ? 'active' : ''}`}
          href="#list"
          data-view="list"
          aria-current={view === 'list' ? 'page' : undefined}
          onClick={(e) => {
            e.preventDefault();
            setView('list');
          }}
        >
          <span className="vt-ic" id="vtList" dangerouslySetInnerHTML={{ __html: ICONS.list }} />
          <span>فهرست</span>
        </a>

        <a
          className={`view-tab ${view === 'map' ? 'active' : ''}`}
          href="#map"
          data-view="map"
          aria-current={view === 'map' ? 'page' : undefined}
          onClick={(e) => {
            e.preventDefault();
            setView('map');
          }}
        >
          <span className="vt-ic" id="vtMap" dangerouslySetInnerHTML={{ __html: ICONS.map }} />
          <span>نقشه</span>
        </a>

        <a
          className={`view-tab ${view === 'inqs' ? 'active' : ''}`}
          href="#inq"
          data-view="inq"
          aria-current={view === 'inqs' ? 'page' : undefined}
          onClick={(e) => {
            e.preventDefault();
            setView('inqs');
          }}
        >
          <span className="vt-ic" id="vtInq" dangerouslySetInnerHTML={{ __html: ICONS.inquiry }} />
          <span>استعلام‌ها</span>
          <b className="vt-badge" id="inqBadge" hidden={activeInquiriesCount === 0}>
            {activeInquiriesCount.toLocaleString('fa-IR')}
          </b>
        </a>
      </nav>

      {/* جستجو */}
      <form className="search" id="searchForm" role="search" autoComplete="off" onSubmit={(e) => e.preventDefault()}>
        <label className="sr" htmlFor="q">جستجوی محصول</label>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.6-3.6" />
        </svg>
        <input
          id="q"
          type="text"
          inputMode="search"
          enterKeyHint="search"
          placeholder="دنبال چه محصولی می‌گردید؟"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button
          className="clear"
          id="clearQ"
          type="button"
          aria-label="پاک کردن جستجو"
          style={{ display: searchQuery ? 'block' : 'none' }}
          onClick={() => setSearchQuery('')}
        >
          ×
        </button>
        <button className="search-sel" id="searchSel" type="button" hidden></button>
      </form>

      {/* وقتی بخش بالا جمع شده: لبه سایه‌دار */}
      <button
        className="min-shade"
        id="minShade"
        type="button"
        aria-label="باز کردن بخش بالا"
        title="باز کردن بخش بالا"
        onClick={() => setIsTopCollapsed(false)}
      >
        <span></span>
      </button>

      {/* چیپ‌های محصولات پیشنهادی */}
      <div className="chips" id="chips" role="group" aria-label="محصولات پیشنهادی">
        {CATS.map((c) => (
          <button
            key={c.id}
            type="button"
            className="chip"
            data-cat={c.id}
            aria-pressed={activeCategory.id === c.id}
            onClick={() => setActiveCategory(c)}
          >
            {c.name}
          </button>
        ))}
      </div>
    </header>
  );
};
