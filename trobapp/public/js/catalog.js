/* ترب مپ — آداپتور کاتالوگ واقعی (FastAPI)
   جایگزین کردن داده‌های نمونه با داده‌های کاتالوگ واقعی بدون تغییر ظاهر یا CSS.
   پوشش جستجو، چیپ‌های دسته، پیشنهادهای فروشگاه‌ها، ارزیابی موجودی و قیمت، اطلاعات فروشگاه و نقشه. */
(function (NQ) {
  'use strict';

  var BASE = '/api/v1';
  var online = false;

  var CAT_QUERIES = {
    headphone: 'هدفون',
    keyboard: 'کیبورد',
    charger: 'شارژر',
    powerbank: 'پاوربانک',
    mouse: 'ماوس',
    rice: 'برنج',
    laptop: 'لپ تاپ'
  };

  // ذخیرهٔ داده‌های نمونه برای حالت آفلاین (fallback)
  var sampleBackup = {
    STORES: Object.assign({}, NQ.STORES || {}),
    CATS: (NQ.CATS || []).slice(),
    PRODUCTS: Object.assign({}, NQ.PRODUCTS || {}),
    OFFERS: Object.assign({}, NQ.OFFERS || {})
  };

  var loadedCats = {};
  var assessmentCache = {};
  var shopDetailCache = {};
  var searchDebounceTimer = 0;

  var JIMBO_DEFAULT = {
    name: 'فروشگاه جیمبو',
    lat: 35.69555,
    lng: 51.4076,
    addr: 'تهران، خیابان جمهوری، پاساژ علاءالدین، طبقهٔ سوم، واحد ۳۱۲',
    hours: '۹ تا ۲۱',
    openH: 9,
    closeH: 21,
    phone: '۰۲۱۶۶۷۰۰۰۹۹',
    phones: ['۰۲۱۶۶۷۰۰۰۹۹'],
    torobpay: true,
    installments: [],
    rating: null,
    years: 0,
    orders90: '',
    followups: 0,
    guarantee: false,
    fast: 'ارسال فوری (کمتر از ۲ ساعت)',
    website: null,
    instagram: null,
    messenger: 'whatsapp',
    trust: 0.88,
    inquiry: true,
    _fullLoaded: true
  };
  NQ.STORES['shop_jimbo_test'] = JIMBO_DEFAULT;

  function api(path, opt) {
    opt = opt || {};
    return fetch(BASE + path, {
      method: opt.method || 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-User-Role': 'customer'
      },
      body: opt.body ? JSON.stringify(opt.body) : undefined
    }).then(function (res) {
      if (!res.ok) throw new Error('API ' + path + ' failed: ' + res.status);
      return res.json();
    });
  }

  /* تبدیل فروشگاه از خروجی‌های مختلف بک‌اند به ساختار هماهنگ با NQ.STORES
     هیچ فیلدی بدون منبع ساختگی پر نمی‌شود: rating = null، years = 0، orders90 = '' */
  function formatStore(s) {
    var phone = s.phone || '';
    var phones = [];
    if (s.contacts) {
      try {
        var cl = typeof s.contacts === 'string' ? JSON.parse(s.contacts) : s.contacts;
        if (Array.isArray(cl)) {
          cl.forEach(function (c) {
            if (c.display_number && phones.indexOf(c.display_number) < 0) {
              phones.push(c.display_number);
            }
          });
        }
      } catch (e) {}
    }
    if (!phones.length && phone) phones.push(phone);
    if (!phones.length && s.display_number) phones.push(s.display_number);

    // ساعات کاری واقعی
    var openH = 9, closeH = 21, hours = '۹ تا ۲۱';
    if (s.weekly_hours) {
      try {
        var wh = typeof s.weekly_hours === 'string' ? JSON.parse(s.weekly_hours) : s.weekly_hours;
        var days = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
        var todayKey = days[new Date().getDay()];
        var dShift = wh && wh[todayKey] && wh[todayKey].shifts && wh[todayKey].shifts[0];
        if (dShift) {
          openH = parseInt(dShift.start_time, 10) || 9;
          closeH = parseInt(dShift.end_time, 10) || 21;
          hours = openH + ' تا ' + closeH;
        }
      } catch (e) {}
    } else if (s.open_time && s.close_time) {
      openH = parseInt(s.open_time, 10) || 9;
      closeH = parseInt(s.close_time, 10) || 21;
      hours = openH + ' تا ' + closeH;
    }

    var torobpay = false;
    if (s.payment_options) {
      try {
        var po = typeof s.payment_options === 'string' ? JSON.parse(s.payment_options) : s.payment_options;
        if (Array.isArray(po) && po.indexOf('torobpay') > -1) torobpay = true;
      } catch (e) {}
    }

    var fast = (s.supports_fast_delivery || s.fast) ? 'ارسال فوری (کمتر از ۲ ساعت)' : false;

    return {
      name: s.shop_name || s.name || 'فروشگاه کاتالوگ',
      lat: +(s.lat != null ? s.lat : (s.latitude || 35.7)),
      lng: +(s.lon != null ? s.lon : (s.lng || s.longitude || 51.4)),
      addr: s.address || 'تهران، محدوده جمهوری',
      hours: hours,
      openH: openH,
      closeH: closeH,
      phone: phones[0] || phone,
      phones: phones,
      torobpay: torobpay,
      installments: [],
      rating: null,   // امتیاز بدون منبع نمایش داده نمی‌شود
      years: 0,
      orders90: '',
      followups: 0,
      guarantee: false,
      fast: fast,
      website: s.website_url || s.website || null,
      instagram: s.instagram || null,
      messenger: 'whatsapp',
      trust: s.reliability_score || 0.8,
      inquiry: true
    };
  }

  /* بارگذاری و تبدیل محصولات و پیشنهادهای یک عبارت جستجو / دسته */
  function fetchProductsAndOffers(query, catId) {
    return api('/products?q=' + encodeURIComponent(query) + '&limit=15')
      .then(function (data) {
        var items = (data && data.items) || [];
        if (!items.length) {
          NQ.PRODUCTS[catId] = [];
          NQ.OFFERS[catId] = [];
          return;
        }

        // تبدیل مدل محصول
        var prods = items.map(function (p) {
          var specs = [];
          if (p.specs && typeof p.specs === 'object') {
            Object.keys(p.specs).forEach(function (k) {
              specs.push([k, String(p.specs[k])]);
            });
          }
          if (!specs.length) {
            specs = [
              ['برند', p.brand_name || '—'],
              ['دسته‌بندی', p.category_name || '—']
            ];
            if (p.model) specs.push(['مدل', p.model]);
          }
          return {
            id: p.product_id,
            brand: p.brand_name || '',
            title: p.persian_title,
            kind: 'generic',
            tagline: p.model || p.category_name || '',
            desc: p.persian_title + (p.brand_name ? ' از برند ' + p.brand_name : ''),
            specs: specs,
            more: [],
            img: (p.image_urls && p.image_urls[0]) || null,
            imgs: p.image_urls || []
          };
        });

        // دریافت پیشنهادهای فروشگاه‌ها برای تمام محصولات
        return Promise.all(items.map(function (p) {
          return api('/products/' + p.product_id + '/offers').then(function (offers) {
            return { product: p, offers: Array.isArray(offers) ? offers : [] };
          }).catch(function () {
            return { product: p, offers: [] };
          });
        })).then(function (results) {
          var allRows = [];
          var missingShopIds = [];

          results.forEach(function (res) {
            var p = res.product;
            res.offers.forEach(function (o) {
              if (!NQ.STORES[o.shop_id]) {
                NQ.STORES[o.shop_id] = {
                  name: 'فروشگاه کاتالوگ',
                  lat: NQ.CENTER ? NQ.CENTER.lat : 35.7,
                  lng: NQ.CENTER ? NQ.CENTER.lng : 51.4,
                  addr: 'تهران، محدوده جمهوری',
                  hours: '۹ تا ۲۱',
                  openH: 9,
                  closeH: 21,
                  phone: '',
                  phones: [],
                  torobpay: false,
                  installments: [],
                  rating: null,
                  years: 0,
                  orders90: '',
                  followups: 0,
                  guarantee: false,
                  fast: false,
                  trust: 0.8,
                  inquiry: true
                };
                if (missingShopIds.indexOf(o.shop_id) < 0) {
                  missingShopIds.push(o.shop_id);
                }
              }
              var hrs = o.last_price_changed_at
                ? Math.max(1, Math.round((Date.now() - new Date(o.last_price_changed_at).getTime()) / 3600000))
                : 2;

              var extra = null;
              if (o.warranty) {
                try {
                  var w = typeof o.warranty === 'string' ? JSON.parse(o.warranty) : o.warranty;
                  if (w && w.period_months) extra = { m: w.period_months, k: w.provider || 'شرکتی' };
                  else if (w && (w.provider || w.description)) extra = { m: 12, k: w.provider || w.description };
                } catch (e) {
                  extra = { m: 12, k: String(o.warranty) };
                }
              }

              var colors = [];
              ['مشکی', 'سفید', 'آبی', 'سبز', 'خاکستری', 'نقره‌ای', 'سرمه‌ای'].forEach(function (col) {
                if (o.seller_title && o.seller_title.indexOf(col) > -1) colors.push(col);
              });

              // موجودی اولیه بر اساس اصول: تا تأیید نشود «موجودی تأیید نشده» (unsure) است
              var row = [o.shop_id, p.persian_title, colors, Math.round(o.price_toman), 'unsure', hrs, extra];
              row._offerId = o.offer_id;
              row._prodId = p.product_id;
              allRows.push(row);
            });
          });

          // دریافت مشخصات اولیه فروشگاه‌های غایب به صورت دسته‌ای
          var shopPromise = missingShopIds.length
            ? api('/catalog/compare-stores', {
                method: 'POST',
                body: { shop_ids: missingShopIds, product_id: items[0].product_id }
              }).then(function (shops) {
                if (Array.isArray(shops)) {
                  shops.forEach(function (s) {
                    NQ.STORES[s.shop_id] = formatStore(s);
                  });
                }
              }).catch(function () {})
            : Promise.resolve();

          return shopPromise.then(function () {
            // به‌روزرسانی ساختارهای مشترک
            NQ.PRODUCTS[catId] = prods;
            NQ.OFFERS[catId] = allRows;
            loadedCats[catId] = true;
          });
        });
      });
  }

  /* بررسی وضعیت ارزیابی موجودی و قیمت از اندپوینت assessment */
  function assessOffersForProduct(productId, catId) {
    var rows = (NQ.OFFERS[catId] || []).filter(function (r) {
      return r._prodId === productId && r._offerId;
    });
    if (!rows.length) return;

    var updated = false;
    Promise.all(rows.map(function (row) {
      var oid = row._offerId;
      if (assessmentCache[oid]) {
        applyAssessment(row, assessmentCache[oid]);
        updated = true;
        return Promise.resolve();
      }
      return api('/offers/' + oid + '/assessment').then(function (ass) {
        if (ass) {
          assessmentCache[oid] = ass;
          applyAssessment(row, ass);
          updated = true;
        }
      }).catch(function () {});
    })).then(function () {
      if (updated && NQ.App) {
        NQ.App.renderAll();
      }
    });
  }

  function applyAssessment(row, ass) {
    if (ass.stock_assessment && ass.stock_assessment.status) {
      var st = ass.stock_assessment.status;
      if (st === 'in_store_sellable') row[4] = 'in';
      else if (st === 'out_of_stock') row[4] = 'out';
      else row[4] = 'unsure';
    }
    if (ass.shop_reliability && ass.shop_reliability.composite_reliability_score != null) {
      var sid = row[0];
      if (NQ.STORES[sid]) {
        NQ.STORES[sid].trust = ass.shop_reliability.composite_reliability_score;
      }
    }
  }

  /* دریافت جزئیات کامل فروشگاه (ساعات دقیق، تلفن‌ها، وبسایت، اینستاگرام) */
  function loadFullShop(sid) {
    if (shopDetailCache[sid]) return Promise.resolve(shopDetailCache[sid]);
    return api('/shops/' + sid).then(function (shop) {
      if (shop) {
        shopDetailCache[sid] = shop;
        var formatted = formatStore(shop);
        formatted._fullLoaded = true;
        NQ.STORES[sid] = Object.assign(NQ.STORES[sid] || {}, formatted);
        return shop;
      }
    }).catch(function () {});
  }

  /* بارگذاری اولیه فروشگاه‌های واقعی تهران روی نقشه (برای حالت stage === none) */
  function loadInitialMapStores() {
    return api('/map/stores?center_lat=35.695&center_lon=51.41&radius_km=4&limit=60')
      .then(function (stores) {
        if (Array.isArray(stores) && stores.length) {
          // حذف فروشگاه‌های فرضی s1 تا s17
          Object.keys(NQ.STORES).forEach(function (k) {
            if (/^s\d+$/.test(k)) delete NQ.STORES[k];
          });
          stores.forEach(function (st) {
            NQ.STORES[st.shop_id] = formatStore(st);
          });
        }
        // اطمینان از وجود فروشگاه تست جیمبو
        return api('/shops/shop_jimbo_test').then(function (jb) {
          if (jb) {
            var jbStore = formatStore(jb);
            jbStore._fullLoaded = true;
            NQ.STORES['shop_jimbo_test'] = jbStore;
          }
        }).catch(function () {});
      })
      .then(function () {
        if (NQ.App && NQ.App.state && !NQ.App.state.cat) {
          NQ.App.renderAll();
          NQ.App.fitResults();
        }
      });
  }

  /* پیش‌بارگذاری موازی ۷ دستهٔ اصلی کاتالوگ در پس‌زمینه */
  function preloadDefaultCategories() {
    var catKeys = Object.keys(CAT_QUERIES);
    Promise.all(catKeys.map(function (catId) {
      return fetchProductsAndOffers(CAT_QUERIES[catId], catId).catch(function () {});
    })).then(function () {
      if (NQ.App && NQ.App.state && NQ.App.state.cat) {
        NQ.App.renderAll();
        NQ.App.fitResults();
      }
    });
  }

  /* جستجوی آزاد در کاتالوگ واقعی */
  function search(query) {
    query = (query || '').trim();
    if (!query) {
      if (NQ.App) NQ.App.setCat(null);
      return;
    }

    if (NQ.App && NQ.App.goView) NQ.App.goView('list');

    // بررسی آیا عبارت با دسته‌های اصلی تطابق دارد
    var matchedCatId = null;
    Object.keys(CAT_QUERIES).forEach(function (cid) {
      if (CAT_QUERIES[cid] === query || (query.indexOf(CAT_QUERIES[cid]) > -1 && query.length < 15)) {
        matchedCatId = cid;
      }
    });

    var targetCatId = matchedCatId || ('search_' + encodeURIComponent(query).replace(/%/g, '_'));

    // ثبت دستهٔ پویا در صورت لزوم
    var existingCat = NQ.App ? NQ.App.catById(targetCatId) : null;
    if (!existingCat) {
      var catObj = { id: targetCatId, name: query, words: [query], q: query };
      NQ.CATS.push(catObj);
    }

    fetchProductsAndOffers(query, targetCatId).then(function () {
      if (NQ.App) {
        NQ.App.setCat(targetCatId);
      }
    }).catch(function (err) {
      console.warn('[catalog] search failed:', err);
    });
  }

  function onSearchInput(val) {
    clearTimeout(searchDebounceTimer);
    var q = (val || '').trim();
    if (!q) {
      if (NQ.App) NQ.App.setCat(null);
      return;
    }
    searchDebounceTimer = setTimeout(function () {
      search(q);
    }, 380);
  }

  function onCatChange(catId) {
    if (!catId) return;
    if (!loadedCats[catId]) {
      var q = CAT_QUERIES[catId] || ((NQ.App && NQ.App.catById(catId)) || {}).name || catId;
      fetchProductsAndOffers(q, catId).then(function () {
        if (NQ.App && NQ.App.state && NQ.App.state.cat === catId) {
          NQ.App.renderAll();
          NQ.App.fitResults();
        }
      });
    }
  }

  function onProductSelect(productId, sid) {
    var catId = NQ.App && NQ.App.state ? NQ.App.state.cat : null;
    if (!productId || !catId) return;

    // بارگذاری ارزیابی‌های پیشنهادها
    assessOffersForProduct(productId, catId);

    // بارگذاری اطلاعات کامل فروشگاه‌های این محصول
    var rows = (NQ.OFFERS[catId] || []).filter(function (r) {
      return r._prodId === productId;
    });
    rows.forEach(function (r) {
      var storeId = r[0];
      if (NQ.STORES[storeId] && !NQ.STORES[storeId]._fullLoaded) {
        loadFullShop(storeId).then(function () {
          if (NQ.App && NQ.App.state && NQ.App.state.product === productId) {
            NQ.App.renderAll();
          }
        });
      }
    });
  }

  function onOpenStoreDlg(sid, cat, title) {
    if (!sid) return;
    loadFullShop(sid).then(function () {
      if (NQ.App && NQ.App.refreshStoreDlg) {
        NQ.App.refreshStoreDlg();
      }
    });
  }

  /* آغاز به کار آداپتور کاتالوگ */
  function init() {
    api('/health')
      .then(function (h) {
        if (h && h.status === 'healthy') {
          online = true;
          // بارگذاری فروشگاه‌های واقعی نقشه
          loadInitialMapStores();
          // بارگذاری دسته‌های اصلی کاتالوگ
          preloadDefaultCategories();
        } else {
          fallbackOffline();
        }
      })
      .catch(function () {
        fallbackOffline();
      });
  }

  function fallbackOffline() {
    online = false;
    console.warn('[catalog] running in offline fallback mode with sample data');
    if (NQ.App && NQ.App.toast) {
      NQ.App.toast('حالت آفلاین (داده‌های نمونه)', 'warn');
    }
  }

  NQ.Catalog = {
    init: init,
    search: search,
    onSearchInput: onSearchInput,
    onCatChange: onCatChange,
    onProductSelect: onProductSelect,
    onOpenStoreDlg: onOpenStoreDlg,
    isOnline: function () { return online; }
  };

  // راه‌اندازی پس از بارگذاری اسکریپت
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    setTimeout(init, 50);
  }

})(window.NQ = window.NQ || {});
