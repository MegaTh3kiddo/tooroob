/* ترب مپ — منوی حساب کاربری
   نام و حساب واردشده، پروفایل (قابل ویرایش)، تنظیمات (حالت نمایش، روش رفت‌وآمد پیش‌فرض، پاک کردن گفتگوها)،
   اشتراک، بازخورد و پشتیبانی، خروج. فعلاً همه‌چیز نمایشی است و در مرورگر ذخیره می‌شود؛
   بعداً به سرویس حساب کاربری ترب وصل می‌شود. */
(function (NQ) {
  'use strict';
  var $ = function (s) { return document.querySelector(s); };
  var api, btn, menu, dlg, root = document.documentElement;
  var PKEY = 'nq-profile-v1', TKEY = 'nq-theme';
  var DEF_PHOTO = 'img/avatar.svg';   // عکس آزمایشی پیش‌فرض
  var profile = { name: 'کاربر ترب', phone: '۰۹۱۲۱۲۳۴۵۶۷', email: '', loggedIn: true, plan: 'free', photo: '' };
  try { var p = JSON.parse(localStorage.getItem(PKEY) || 'null'); if (p) Object.keys(p).forEach(function (k) { profile[k] = p[k]; }); } catch (e) {}
  function saveProfile() { try { localStorage.setItem(PKEY, JSON.stringify(profile)); } catch (e) {} }

  function svg(inner) { return '<svg class="ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + inner + '</svg>'; }
  var I = {
    user: svg('<circle cx="12" cy="8.5" r="3.8"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>'),
    gear: svg('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>'),
    crown: svg('<path d="M3.5 8l4.5 4 4-6 4 6 4.5-4-2 10.5h-13z"/>'),
    chat: svg('<path d="M20 12a8 8 0 0 1-11.6 7.1L4 20l1-4.2A8 8 0 1 1 20 12z"/><path d="M8.5 11h7M8.5 14h4"/>'),
    out: svg('<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="M10 16l-4-4 4-4M6 12h10"/>'),
    sun: svg('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
    moon: svg('<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>'),
    auto: svg('<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17a8.5 8.5 0 0 0 0-17z" fill="currentColor"/>'),
    login: svg('<path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3"/><path d="M14 16l4-4-4-4M18 12H8"/>')
  };

  /* ---- حالت نمایش: روشن، تاریک یا خودکار (مثل سیستم) ---- */
  function themeMode() { return root.getAttribute('data-theme') || 'system'; }
  function setTheme(m) {
    if (m === 'system') root.removeAttribute('data-theme'); else root.setAttribute('data-theme', m);
    try { if (m === 'system') localStorage.removeItem(TKEY); else localStorage.setItem(TKEY, m); } catch (e) {}
    Array.prototype.forEach.call(document.querySelectorAll('[data-theme-set]'), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-theme-set') === m)); });
  }
  try { var t = localStorage.getItem(TKEY); if (t) root.setAttribute('data-theme', t); } catch (e) {}
  function themeSeg() {
    var cur = themeMode();
    return '<div class="am-seg" role="group" aria-label="حالت نمایش">' + [['light', 'روشن', I.sun], ['dark', 'تاریک', I.moon], ['system', 'خودکار', I.auto]].map(function (x) {
      return '<button type="button" data-theme-set="' + x[0] + '" aria-pressed="' + (cur === x[0]) + '">' + x[2] + '<span>' + x[1] + '</span></button>';
    }).join('') + '</div>';
  }

  function initial() { return (profile.name || 'ک').trim().charAt(0); }
  /* عکس پروفایل (عکس انتخابی کاربر یا عکس آزمایشی) */
  function avatar(cls) { return '<span class="acct-av ' + (cls || '') + '"><img src="' + api.esc(profile.photo || DEF_PHOTO) + '" alt=""></span>'; }
  /* عکس انتخاب‌شده کوچک می‌شود (۱۶۰ پیکسل) تا در مرورگر جا بگیرد */
  function readPhoto(file, done) {
    if (!file || !/^image\//.test(file.type)) return;
    var fr = new FileReader();
    fr.onload = function () {
      var im = new Image();
      im.onload = function () {
        var c = document.createElement('canvas'), z = 160, sc = Math.max(z / im.width, z / im.height);
        c.width = c.height = z;
        var g = c.getContext('2d'); g.drawImage(im, (z - im.width * sc) / 2, (z - im.height * sc) / 2, im.width * sc, im.height * sc);
        done(c.toDataURL('image/jpeg', .85));
      };
      im.src = fr.result;
    };
    fr.readAsDataURL(file);
  }
  function renderBtn() {
    btn.innerHTML = profile.loggedIn ? avatar() : '<span class="acct-av off">' + I.user + '</span>';
    btn.setAttribute('aria-label', profile.loggedIn ? 'حساب کاربری: ' + profile.name : 'ورود به حساب');
  }
  function renderMenu() {
    var head = profile.loggedIn
      ? '<div class="am-head">' + avatar('lg') + '<div class="am-who"><b>' + api.esc(profile.name) + '</b><small dir="ltr">' + api.esc(profile.phone || profile.email || '') + '</small></div></div>'
      : '<div class="am-head"><span class="acct-av lg off">' + I.user + '</span><div class="am-who"><b>وارد نشده‌ای</b><small>برای ذخیرهٔ گفتگوها و برنامه وارد شو</small></div></div>' +
        '<button type="button" class="am-login" role="menuitem" data-acct="login">' + I.login + '<span>ورود به حساب</span></button>';
    menu.innerHTML = head +
      (profile.loggedIn ? '<button type="button" class="am-item" role="menuitem" data-acct="profile">' + I.user + '<span>پروفایل</span></button>' : '') +
      '<button type="button" class="am-item" role="menuitem" data-acct="settings">' + I.gear + '<span>تنظیمات</span></button>' +
      (profile.loggedIn ? '<button type="button" class="am-item" role="menuitem" data-acct="sub">' + I.crown + '<span>اشتراک</span><em class="am-tag">' + (profile.plan === 'plus' ? 'پلاس' : 'رایگان') + '</em></button>' : '') +
      '<button type="button" class="am-item" role="menuitem" data-acct="support">' + I.chat + '<span>بازخورد و پشتیبانی</span></button>' +
      themeSeg() +
      (profile.loggedIn ? '<hr class="am-sep"><button type="button" class="am-item danger" role="menuitem" data-acct="logout">' + I.out + '<span>خروج</span></button>' : '');
  }
  function openMenu() {
    renderMenu(); menu.hidden = false; btn.setAttribute('aria-expanded', 'true');
    var f = menu.querySelector('[role="menuitem"]'); if (f) f.focus();
  }
  function closeMenu(focusBtn) { if (menu.hidden) return; menu.hidden = true; btn.setAttribute('aria-expanded', 'false'); if (focusBtn) btn.focus(); }

  /* ---- پنجره‌ها ---- */
  function openDlg(title, html) {
    $('#acctTitle').textContent = title; $('#acctBody').innerHTML = html;
    if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
    var f = dlg.querySelector('input,textarea,select'); if (f) f.focus();
  }
  function profileHTML() {
    return '<form class="af" id="afProfile">' +
      '<div class="af-av">' + avatar('xl') + '<div class="af-av-acts"><label class="af-photo">تغییر عکس<input type="file" accept="image/*" id="afPhoto" hidden></label>' +
        (profile.photo ? '<button type="button" class="link-btn" data-photo-reset>عکس پیش‌فرض</button>' : '') + '</div></div>' +
      '<label class="af-l">نام<input name="name" required maxlength="40" value="' + api.esc(profile.name) + '"></label>' +
      '<label class="af-l">شمارهٔ موبایل<input name="phone" dir="ltr" inputmode="tel" maxlength="14" value="' + api.esc(profile.phone) + '"></label>' +
      '<label class="af-l">ایمیل <small>(اختیاری)</small><input name="email" type="email" dir="ltr" maxlength="80" value="' + api.esc(profile.email) + '"></label>' +
      '<footer class="af-foot"><button type="button" class="fd-reset" data-acct-close>انصراف</button><button type="submit" class="fd-done">ذخیره</button></footer></form>';
  }
  function settingsHTML() {
    var T = api.Travel;
    return '<div class="af">' +
      '<section class="af-sec"><h3>حالت نمایش</h3>' + themeSeg() + '</section>' +
      '<section class="af-sec"><h3>روش رفت‌وآمد پیش‌فرض</h3><div class="af-chips">' + T.MENU.map(function (id) {
        return '<button type="button" class="fc' + (T.mode === id ? ' on' : '') + '" data-travel-set="' + id + '" aria-pressed="' + (T.mode === id) + '">' + api.icons[id] + T.label(id) + '</button>';
      }).join('') + '</div></section>' +
      '<section class="af-sec"><h3>شهر پیش‌فرض</h3><div class="af-chips">' + api.cities.map(function (c) {
        var on = api.city() === c.id;
        return '<button type="button" class="fc' + (on ? ' on' : '') + '" data-city-set="' + c.id + '" aria-pressed="' + on + '"' + (c.active ? '' : ' disabled title="به‌زودی"') + '>' + api.esc(c.name) + (c.active ? '' : ' <small>به‌زودی</small>') + '</button>';
      }).join('') + '</div></section>' +
      '<section class="af-sec"><h3>تربچت</h3><button type="button" class="af-danger" data-clear-chats>پاک کردن همهٔ گفتگوها</button></section>' +
    '</div>';
  }
  function subHTML() {
    return '<div class="af">' +
      '<div class="sub-card cur"><div class="sub-h"><b>رایگان</b><em>اشتراک فعلی</em></div><ul><li>جستجو و مقایسهٔ قیمت</li><li>نقشه و برنامهٔ سر زدن</li><li>تربچت با محدودیت روزانه</li></ul></div>' +
      '<div class="sub-card plus"><div class="sub-h"><b>' + I.crown + 'ترب پلاس</b><em>به‌زودی</em></div><ul><li>تربچت بدون محدودیت</li><li>خبر دادن وقتی قیمت پایین آمد</li><li>استعلام قیمت سریع‌تر از فروشگاه‌ها</li></ul>' +
      '<button type="button" class="fd-done" disabled>به‌زودی</button></div>' +
    '</div>';
  }
  var SUP = {
    feedback: { t: 'بازخورد', q: 'نظرت درباره‌ی تربچت چیه؟' },
    bug: { t: 'مشکل', q: 'چه مشکلی پیش اومد؟' },
    idea: { t: 'پیشنهاد', q: 'چه پیشنهادی داری؟' }
  };
  function supportHTML() {
    return '<form class="af" id="afSupport">' +
      '<p class="af-lead">نظر، پیشنهاد یا مشکلت رو با ما در میون بذار.</p>' +
      '<p class="af-note">این بخش برای پیگیری سفارش نیست. اگه درباره سفارشی که از ترب خریدی مشکلی داری، <a href="' + api.LINKS.guarantee + '" target="_blank" rel="noopener">راهنمای پیگیری سفارش</a> رو ببین.</p>' +
      '<div class="am-seg sup-seg" role="radiogroup" aria-label="نوع پیام">' + Object.keys(SUP).map(function (k, i) {
        return '<button type="button" role="radio" data-sup="' + k + '" aria-checked="' + !i + '" aria-pressed="' + !i + '"><span>' + SUP[k].t + '</span></button>';
      }).join('') + '</div>' +
      '<label class="af-l"><span id="supQ">' + SUP.feedback.q + '</span><textarea name="msg" rows="5" maxlength="2000" required></textarea><small class="af-cnt" id="supCnt">۰ / ۲۰۰۰</small></label>' +
      '<label class="af-l">راه ارتباطی برای پیگیری <small>(اختیاری)</small><input name="contact" dir="ltr" maxlength="80" placeholder="ایمیل یا شمارهٔ موبایل"></label>' +
      '<footer class="af-foot"><button type="button" class="fd-reset" data-acct-close>انصراف</button><button type="submit" class="fd-done" id="supSend" disabled>ارسال</button></footer></form>';
  }

  function act(k) {
    closeMenu(false);
    if (k === 'profile') openDlg('پروفایل', profileHTML());
    else if (k === 'settings') openDlg('تنظیمات', settingsHTML());
    else if (k === 'sub') openDlg('اشتراک', subHTML());
    else if (k === 'support') openDlg('بازخورد و پشتیبانی', supportHTML());
    else if (k === 'logout') { profile.loggedIn = false; saveProfile(); renderBtn(); api.toast('از حسابت خارج شدی.', 'info'); }
    else if (k === 'login') { profile.loggedIn = true; saveProfile(); renderBtn(); api.toast('وارد حسابت شدی. (نسخهٔ آزمایشی)', 'success'); }
  }

  NQ.Account = {
    init: function (a) {
      api = a; btn = $('#acctBtn'); menu = $('#acctMenu'); dlg = $('#acctDlg');
      renderBtn();
      btn.addEventListener('click', function () { if (menu.hidden) openMenu(); else closeMenu(true); });
      document.addEventListener('click', function (e) { if (!menu.hidden && !e.target.closest('#acct')) closeMenu(false); });
      menu.addEventListener('keydown', function (e) {
        var items = Array.prototype.slice.call(menu.querySelectorAll('[role="menuitem"],[data-theme-set]')), i = items.indexOf(document.activeElement);
        if (e.key === 'ArrowDown') { e.preventDefault(); items[(i + 1) % items.length].focus(); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
        else if (e.key === 'Escape') { e.stopPropagation(); closeMenu(true); }
        else if (e.key === 'Tab') closeMenu(false);
      });
      menu.addEventListener('click', function (e) {
        var t = e.target.closest('[data-theme-set]'); if (t) { setTheme(t.getAttribute('data-theme-set')); return; }
        t = e.target.closest('[data-acct]'); if (t) act(t.getAttribute('data-acct'));
      });
      $('#acctClose').addEventListener('click', function () { dlg.close(); });
      dlg.addEventListener('click', function (e) {
        var t;
        if (e.target === dlg || e.target.closest('[data-acct-close]')) { dlg.close(); return; }
        if ((t = e.target.closest('[data-theme-set]'))) { setTheme(t.getAttribute('data-theme-set')); return; }
        if ((t = e.target.closest('[data-travel-set]'))) {
          api.Travel.set(t.getAttribute('data-travel-set')); api.onTravel();
          Array.prototype.forEach.call(dlg.querySelectorAll('[data-travel-set]'), function (b) { var on = b === t; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
          return;
        }
        if ((t = e.target.closest('[data-city-set]'))) {
          if (!api.setCity(t.getAttribute('data-city-set'))) return;
          Array.prototype.forEach.call(dlg.querySelectorAll('[data-city-set]'), function (b) { var on = b === t; b.classList.toggle('on', on); b.setAttribute('aria-pressed', String(on)); });
          return;
        }
        if (e.target.closest('[data-photo-reset]')) { profile.photo = ''; saveProfile(); renderBtn(); $('#acctBody').innerHTML = profileHTML(); return; }
        if (e.target.closest('[data-clear-chats]')) {
          if (!window.confirm('همهٔ گفتگوهای تربچت پاک شوند؟')) return;
          api.clearChats(); api.toast('گفتگوها پاک شد.', 'info'); return;
        }
        if ((t = e.target.closest('[data-sup]'))) {
          Array.prototype.forEach.call(dlg.querySelectorAll('[data-sup]'), function (b) { var on = b === t; b.setAttribute('aria-checked', String(on)); b.setAttribute('aria-pressed', String(on)); });
          $('#supQ').textContent = SUP[t.getAttribute('data-sup')].q;
        }
      });
      dlg.addEventListener('change', function (e) {
        if (e.target.id !== 'afPhoto') return;
        readPhoto(e.target.files[0], function (url) {
          profile.photo = url; saveProfile(); renderBtn();
          var av = dlg.querySelector('.af-av .acct-av img'); if (av) av.src = url;
          api.toast('عکس پروفایل عوض شد.', 'success');
        });
      });
      dlg.addEventListener('input', function (e) {
        if (e.target.name !== 'msg') return;
        $('#supCnt').textContent = api.fa(e.target.value.length) + ' / ۲۰۰۰';
        $('#supSend').disabled = !e.target.value.trim();
      });
      dlg.addEventListener('submit', function (e) {
        e.preventDefault();
        var f = e.target;
        if (f.id === 'afProfile') {
          var el = function (n) { return f.elements.namedItem(n).value.trim(); };
          profile.name = el('name') || profile.name; profile.phone = el('phone'); profile.email = el('email');
          saveProfile(); renderBtn(); dlg.close(); api.toast('پروفایل ذخیره شد.', 'success');
        } else if (f.id === 'afSupport') {
          dlg.close(); api.toast('پیامت رسید؛ ممنون که نوشتی.', 'success');
        }
      });
    }
  };
})(window.NQ = window.NQ || {});
