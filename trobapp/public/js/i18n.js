/**
 * TorobMap Bilingual Support (Persian default, English optional)
 * Manages language switching, RTL/LTR layout toggling, and UI dictionary updates.
 */
(function () {
  'use strict';

  var LANG_KEY = 'torob_lang';
  var currentLang = 'fa';

  var DICT = {
    fa: {
      brand: 'ترب مپ',
      cityName: 'تهران',
      langBadge: 'EN',
      langTitle: 'Switch to English',
      viewAgent: 'تربچت',
      viewList: 'فهرست',
      viewMap: 'نقشه',
      viewInq: 'استعلام‌ها',
      searchPlaceholder: 'دنبال چه محصولی می‌گردید؟',
      sortPrice: 'ارزان‌ترین',
      sortNear: 'نزدیک‌ترین',
      sortSmart: 'پیشنهادی',
      travelLabel: 'رفت‌وآمد:',
      filterBtn: 'فیلتر',
      agentHelloTitle: 'من تربچتم، دستیار خریدت',
      agentHelloDesc: 'قیمت بپرس، مدل‌ها رو مقایسه کن یا بر اساس بودجه انتخاب کن.',
      agentInputPlaceholder: 'دنبال چه چیزی می‌گردین؟',
      agentSideTitle: 'سر زدن‌ها',
      newChatBtn: 'گفت‌وگوی جدید',
      tabResults: 'نتایج جستجو',
      tabPlan: 'برنامهٔ سر زدن',
      mapHint: 'نقطهٔ «شما» را بکشید تا موقعیت عوض شود'
    },
    en: {
      brand: 'TorobMap',
      cityName: 'Tehran',
      langBadge: 'FA',
      langTitle: 'تغییر به فارسی (پیش‌فرض)',
      viewAgent: 'TorobChat',
      viewList: 'Stores',
      viewMap: 'Map View',
      viewInq: 'Inquiries',
      searchPlaceholder: 'What product are you looking for?',
      sortPrice: 'Cheapest',
      sortNear: 'Nearest',
      sortSmart: 'Recommended',
      travelLabel: 'Transit:',
      filterBtn: 'Filter',
      agentHelloTitle: "I'm TorobChat, your shopping assistant",
      agentHelloDesc: 'Ask prices, compare models, or choose based on your budget.',
      agentInputPlaceholder: 'What are you looking for?',
      agentSideTitle: 'Store Visits',
      newChatBtn: 'New Chat',
      tabResults: 'Search Results',
      tabPlan: 'Visit Itinerary',
      mapHint: 'Drag the pin to change your location'
    }
  };

  function applyLanguage(lang) {
    currentLang = lang === 'en' ? 'en' : 'fa';
    try {
      localStorage.setItem(LANG_KEY, currentLang);
    } catch (e) {}

    var d = DICT[currentLang];
    var isEn = currentLang === 'en';

    document.documentElement.lang = isEn ? 'en' : 'fa';
    document.documentElement.dir = isEn ? 'ltr' : 'rtl';

    // Update Language Button
    var btn = document.getElementById('langToggleBtn');
    var badge = document.getElementById('langBadge');
    if (badge) badge.textContent = d.langBadge;
    if (btn) btn.title = d.langTitle;

    // Brand and City
    var brand = document.querySelector('.brand-name');
    if (brand) brand.textContent = d.brand;
    var cityName = document.getElementById('cityName');
    if (cityName) cityName.textContent = d.cityName;

    // View Navigation Tabs
    var tabAgent = document.querySelector('[data-view="agent"] span:last-child');
    if (tabAgent) tabAgent.textContent = d.viewAgent;
    var tabList = document.querySelector('[data-view="list"] span:last-child');
    if (tabList) tabList.textContent = d.viewList;
    var tabMap = document.querySelector('[data-view="map"] span:last-child');
    if (tabMap) tabMap.textContent = d.viewMap;
    var tabInq = document.querySelector('[data-view="inq"] span:nth-child(2)');
    if (tabInq) tabInq.textContent = d.viewInq;

    // Search bar
    var qInput = document.getElementById('q');
    if (qInput) qInput.placeholder = d.searchPlaceholder;

    // Sorting radio buttons
    var sortPrice = document.querySelector('[data-sort="price"]');
    if (sortPrice) sortPrice.textContent = d.sortPrice;
    var sortNear = document.querySelector('[data-sort="near"]');
    if (sortNear) sortNear.textContent = d.sortNear;
    var sortSmart = document.querySelector('[data-sort="smart"]');
    if (sortSmart) sortSmart.textContent = d.sortSmart;

    // Travel & Filter
    var travelL = document.querySelector('.travel-l');
    if (travelL) travelL.textContent = d.travelLabel;
    var filterText = document.querySelector('.filter-btn span:last-child');
    if (filterText) filterText.textContent = d.filterBtn;

    // TorobChat elements
    var agTitle = document.querySelector('.ag-hello h2');
    if (agTitle) agTitle.textContent = d.agentHelloTitle;
    var agDesc = document.querySelector('.ag-hello p');
    if (agDesc) agDesc.textContent = d.agentHelloDesc;
    var agInput = document.getElementById('agInput');
    if (agInput) agInput.placeholder = d.agentInputPlaceholder;
    var agSideH = document.querySelector('.ag-side-h h3');
    if (agSideH) agSideH.textContent = d.agentSideTitle;
    var newChatSpan = document.querySelector('#agHNew span');
    if (newChatSpan) newChatSpan.textContent = d.newChatBtn;

    // Map Hints
    var hint = document.getElementById('hint');
    if (hint) hint.textContent = d.mapHint;
  }

  function init() {
    var saved = 'fa';
    try {
      saved = localStorage.getItem(LANG_KEY) || 'fa';
    } catch (e) {}

    // Ensure button exists or observe
    var btn = document.getElementById('langToggleBtn');
    if (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        applyLanguage(currentLang === 'fa' ? 'en' : 'fa');
      });
    }

    if (saved === 'en') {
      applyLanguage('en');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.TorobI18n = {
    apply: applyLanguage,
    getLang: function () { return currentLang; }
  };
})();
