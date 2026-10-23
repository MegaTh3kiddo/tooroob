'use client';

import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { SvgIcon } from '../../data/icons';
import { TravelMode } from '../../types';

export const AccountModal: React.FC = () => {
  const {
    activeModal,
    modalData,
    closeModal,
    user,
    login,
    logout,
    theme,
    toggleTheme,
    travelMode,
    setTravelMode,
    city,
    setCity,
    cities,
    clearChat,
  } = useApp();

  const tab = modalData?.tab || (user.isLoggedIn ? 'profile' : 'login');
  const [currentTab, setCurrentTab] = useState<'profile' | 'settings' | 'sub' | 'support' | 'login'>(tab);

  // Profile state
  const [name, setName] = useState('کاربر ترب');
  const [phone, setPhone] = useState(user.phone || '۰۹۱۲۱۲۳۴۵۶۷');
  const [email, setEmail] = useState('');

  // Support state
  const [supType, setSupType] = useState<'feedback' | 'bug' | 'idea'>('feedback');
  const [supMsg, setSupMsg] = useState('');
  const [supContact, setSupContact] = useState('');

  // Login state
  const [loginPhone, setLoginPhone] = useState('');
  const [loginStep, setLoginStep] = useState<'phone' | 'otp'>('phone');
  const [loginOtp, setLoginOtp] = useState('');

  if (activeModal !== 'account') return null;

  const getTitle = () => {
    switch (currentTab) {
      case 'profile':
        return 'پروفایل';
      case 'settings':
        return 'تنظیمات';
      case 'sub':
        return 'اشتراک';
      case 'support':
        return 'بازخورد و پشتیبانی';
      case 'login':
        return 'ورود به حساب';
      default:
        return 'حساب کاربری';
    }
  };

  const handleProfileSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    closeModal();
  };

  const handleSupportSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (supMsg.trim()) {
      closeModal();
    }
  };

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (loginStep === 'phone' && loginPhone.length >= 10) {
      setLoginStep('otp');
    } else if (loginStep === 'otp') {
      login(loginPhone);
      closeModal();
    }
  };

  const supQuestions = {
    feedback: 'نظرت درباره‌ی تربچت چیه؟',
    bug: 'چه مشکلی پیش اومد؟',
    idea: 'چه پیشنهادی داری؟',
  };

  const travelModes: { id: TravelMode; label: string; icon: string }[] = [
    { id: 'walk', label: 'پیاده', icon: 'walk' },
    { id: 'car', label: 'خودرو', icon: 'car' },
    { id: 'moto', label: 'موتور', icon: 'motor' },
    { id: 'transit', label: 'حمل‌ونقل عمومی', icon: 'bus' },
  ];

  return (
    <div className="modal-backdrop" onClick={closeModal}>
      <dialog className="fdlg acctdlg" id="acctDlg" open onClick={(e) => e.stopPropagation()} aria-labelledby="acctTitle">
        <header className="fd-head">
          <h2 id="acctTitle">{getTitle()}</h2>
          <button type="button" className="icon-btn sm" id="acctClose" onClick={closeModal} aria-label="بستن">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>

        <div className="acct-body" id="acctBody">
          {currentTab === 'profile' && (
            <form className="af" id="afProfile" onSubmit={handleProfileSubmit}>
              <div className="af-av">
                <span className="acct-av xl">ک</span>
                <div className="af-av-acts">
                  <label className="af-photo">
                    تغییر عکس
                    <input type="file" accept="image/*" id="afPhoto" hidden />
                  </label>
                </div>
              </div>
              <label className="af-l">
                نام
                <input
                  name="name"
                  required
                  maxLength={40}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </label>
              <label className="af-l">
                شمارهٔ موبایل
                <input
                  name="phone"
                  dir="ltr"
                  inputMode="tel"
                  maxLength={14}
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </label>
              <label className="af-l">
                ایمیل <small>(اختیاری)</small>
                <input
                  name="email"
                  type="email"
                  dir="ltr"
                  maxLength={80}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>
              <footer className="af-foot">
                <button type="button" className="fd-reset" onClick={closeModal}>
                  انصراف
                </button>
                <button type="submit" className="fd-done">
                  ذخیره
                </button>
              </footer>
            </form>
          )}

          {currentTab === 'settings' && (
            <div className="af">
              <section className="af-sec">
                <h3>حالت نمایش</h3>
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
              </section>

              <section className="af-sec">
                <h3>روش رفت‌وآمد پیش‌فرض</h3>
                <div className="af-chips">
                  {travelModes.map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      className={`fc ${travelMode === m.id ? 'on' : ''}`}
                      onClick={() => setTravelMode(m.id)}
                      aria-pressed={travelMode === m.id}
                    >
                      <SvgIcon name={m.icon} size={15} />
                      {m.label}
                    </button>
                  ))}
                </div>
              </section>

              <section className="af-sec">
                <h3>شهر پیش‌فرض</h3>
                <div className="af-chips">
                  {cities.map((c) => {
                    const on = city.id === c.id;
                    return (
                      <button
                        key={c.id}
                        type="button"
                        className={`fc ${on ? 'on' : ''}`}
                        onClick={() => {
                          if (c.active) setCity(c);
                        }}
                        aria-pressed={on}
                        disabled={!c.active}
                        title={!c.active ? 'به‌زودی' : undefined}
                      >
                        {c.name}
                        {!c.active && <small> به‌زودی</small>}
                      </button>
                    );
                  })}
                </div>
              </section>

              <section className="af-sec">
                <h3>تربچت</h3>
                <button
                  type="button"
                  className="af-danger"
                  onClick={() => {
                    clearChat();
                    closeModal();
                  }}
                >
                  پاک کردن همهٔ گفتگوها
                </button>
              </section>
            </div>
          )}

          {currentTab === 'sub' && (
            <div className="af">
              <div className="sub-card cur">
                <div className="sub-h">
                  <b>رایگان</b>
                  <em>اشتراک فعلی</em>
                </div>
                <ul>
                  <li>جستجو و مقایسهٔ قیمت</li>
                  <li>نقشه و برنامهٔ سر زدن</li>
                  <li>تربچت با محدودیت روزانه</li>
                </ul>
              </div>
              <div className="sub-card plus">
                <div className="sub-h">
                  <b>
                    <svg className="ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M3.5 8l4.5 4 4-6 4 6 4.5-4-2 10.5h-13z" />
                    </svg>
                    ترب پلاس
                  </b>
                  <em>به‌زودی</em>
                </div>
                <ul>
                  <li>تربچت بدون محدودیت</li>
                  <li>خبر دادن وقتی قیمت پایین آمد</li>
                  <li>استعلام قیمت سریع‌تر از فروشگاه‌ها</li>
                </ul>
                <button type="button" className="fd-done" disabled>
                  به‌زودی
                </button>
              </div>
            </div>
          )}

          {currentTab === 'support' && (
            <form className="af" id="afSupport" onSubmit={handleSupportSubmit}>
              <p className="af-lead">نظر، پیشنهاد یا مشکلت رو با ما در میون بذار.</p>
              <p className="af-note">
                این بخش برای پیگیری سفارش نیست. اگه درباره سفارشی که از ترب خریدی مشکلی داری،{' '}
                <a href="https://torob.com/pages/guarantee/" target="_blank" rel="noopener noreferrer">
                  راهنمای پیگیری سفارش
                </a>{' '}
                رو ببین.
              </p>
              <div className="am-seg sup-seg" role="radiogroup" aria-label="نوع پیام">
                <button
                  type="button"
                  role="radio"
                  data-sup="feedback"
                  aria-checked={supType === 'feedback'}
                  onClick={() => setSupType('feedback')}
                >
                  <span>بازخورد</span>
                </button>
                <button
                  type="button"
                  role="radio"
                  data-sup="bug"
                  aria-checked={supType === 'bug'}
                  onClick={() => setSupType('bug')}
                >
                  <span>مشکل</span>
                </button>
                <button
                  type="button"
                  role="radio"
                  data-sup="idea"
                  aria-checked={supType === 'idea'}
                  onClick={() => setSupType('idea')}
                >
                  <span>پیشنهاد</span>
                </button>
              </div>
              <label className="af-l">
                <span id="supQ">{supQuestions[supType]}</span>
                <textarea
                  name="msg"
                  rows={5}
                  maxLength={2000}
                  required
                  value={supMsg}
                  onChange={(e) => setSupMsg(e.target.value)}
                />
                <small className="af-cnt" id="supCnt">
                  {supMsg.length.toLocaleString('fa-IR')} / ۲۰۰۰
                </small>
              </label>
              <label className="af-l">
                راه ارتباطی برای پیگیری <small>(اختیاری)</small>
                <input
                  name="contact"
                  dir="ltr"
                  maxLength={80}
                  placeholder="ایمیل یا شمارهٔ موبایل"
                  value={supContact}
                  onChange={(e) => setSupContact(e.target.value)}
                />
              </label>
              <footer className="af-foot">
                <button type="button" className="fd-reset" onClick={closeModal}>
                  انصراف
                </button>
                <button type="submit" className="fd-done" id="supSend" disabled={!supMsg.trim()}>
                  ارسال
                </button>
              </footer>
            </form>
          )}

          {currentTab === 'login' && (
            <form onSubmit={handleLoginSubmit} className="af">
              <p className="af-lead">
                برای ثبت استعلام‌ها و همگام‌سازی برنامهٔ سر زدن در دستگاه‌های خود، شماره تلفن همراه خود را وارد کنید.
              </p>
              {loginStep === 'phone' ? (
                <>
                  <label className="af-l">
                    شماره موبایل
                    <input
                      type="tel"
                      dir="ltr"
                      placeholder="۰۹۱۲۳۴۵۶۷۸۹"
                      value={loginPhone}
                      onChange={(e) => setLoginPhone(e.target.value)}
                      autoFocus
                    />
                  </label>
                  <footer className="af-foot">
                    <button type="button" className="fd-reset" onClick={closeModal}>
                      انصراف
                    </button>
                    <button type="submit" className="fd-done" disabled={loginPhone.length < 10}>
                      ارسال کد تایید
                    </button>
                  </footer>
                </>
              ) : (
                <>
                  <p className="af-note">
                    کد تایید ۴ رقمی ارسال شده به {loginPhone} را وارد کنید. (برای تست: هر ۴ رقمی معتبر است)
                  </p>
                  <label className="af-l">
                    کد تایید
                    <input
                      type="text"
                      dir="ltr"
                      maxLength={6}
                      placeholder="۱۲۳۴"
                      value={loginOtp}
                      onChange={(e) => setLoginOtp(e.target.value)}
                      autoFocus
                    />
                  </label>
                  <footer className="af-foot">
                    <button type="button" className="fd-reset" onClick={() => setLoginStep('phone')}>
                      تغییر شماره
                    </button>
                    <button type="submit" className="fd-done" disabled={loginOtp.length < 4}>
                      ورود
                    </button>
                  </footer>
                </>
              )}
            </form>
          )}
        </div>
      </dialog>
    </div>
  );
};
