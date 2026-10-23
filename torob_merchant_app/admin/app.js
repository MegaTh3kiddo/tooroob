const API_BASE = '/api';

// Tab switching
function switchTab(tabId) {
  document.querySelectorAll('section[id^="tab-"]').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('border-torob-red', 'text-torob-red', 'font-bold');
    btn.classList.add('border-transparent', 'text-slate-500', 'font-medium');
  });

  const targetTab = document.getElementById(`tab-${tabId}`);
  const targetBtn = document.getElementById(`tab-btn-${tabId}`);
  if (targetTab) targetTab.classList.remove('hidden');
  if (targetBtn) {
    targetBtn.classList.add('border-torob-red', 'text-torob-red', 'font-bold');
    targetBtn.classList.remove('border-transparent', 'text-slate-500', 'font-medium');
  }

  if (tabId === 'pushlogs') loadPushLogs();
  if (tabId === 'settings') {
    loadSchedulerConfig();
    loadStores();
  }
  if (tabId === 'changerequests') loadShopChangeRequests();
}

// Format numbers in Persian
function toPersianDigits(n) {
  if (n === null || n === undefined) return '';
  const id = ['۰','۱','۲','۳','۴','۵','۶','۷','۸','۹'];
  return n.toString().replace(/[0-9]/g, function(w){
    return id[+w];
  });
}

function formatPrice(num) {
  if (!num) return '۰ تومان';
  return toPersianDigits(num.toLocaleString('fa-IR')) + ' تومان';
}

// Fetch inquiries & statistics
async function loadInquiries() {
  try {
    const res = await fetch(`${API_BASE}/admin/inquiries?limit=50`);
    if (!res.ok) return;
    const inquiries = await res.json();

    // Stats
    let total = inquiries.length;
    let active = inquiries.filter(i => i.status === 'ACTIVE').length;
    let answered = inquiries.filter(i => i.status === 'ANSWERED').length;
    let expired = inquiries.filter(i => i.status === 'EXPIRED').length;

    document.getElementById('stat-total').innerText = toPersianDigits(total);
    document.getElementById('stat-active').innerText = toPersianDigits(active);
    document.getElementById('stat-answered').innerText = toPersianDigits(answered);
    document.getElementById('stat-expired').innerText = toPersianDigits(expired);

    // Table rows
    const tbody = document.getElementById('inquiries-table-body');
    if (!inquiries.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-slate-400">هنوز استعلامی ثبت نشده است. از تب «شبیه‌ساز ارسال استعلام» یک استعلام نمونه ایجاد کنید.</td></tr>`;
      return;
    }

    tbody.innerHTML = inquiries.map(inq => {
      let statusBadge = '';
      if (inq.status === 'ACTIVE') {
        statusBadge = `<span class="bg-amber-100 text-amber-800 px-2.5 py-1 rounded-full text-[11px] font-bold">در انتظار پاسخ</span>`;
      } else if (inq.status === 'ANSWERED') {
        statusBadge = `<span class="bg-emerald-100 text-emerald-800 px-2.5 py-1 rounded-full text-[11px] font-bold">پاسخ داده شد</span>`;
      } else if (inq.status === 'EXPIRED') {
        statusBadge = `<span class="bg-rose-100 text-rose-800 px-2.5 py-1 rounded-full text-[11px] font-bold">منقضی شده</span>`;
      } else {
        statusBadge = `<span class="bg-slate-100 text-slate-800 px-2.5 py-1 rounded-full text-[11px] font-bold">${inq.status}</span>`;
      }

      // Remaining time
      let remainingDisplay = '-';
      if (inq.status === 'ACTIVE') {
        const rem = inq.remaining_seconds;
        const mins = Math.floor(rem / 60);
        const secs = rem % 60;
        remainingDisplay = `<span class="font-bold text-amber-700">${toPersianDigits(mins)}:${toPersianDigits(secs < 10 ? '0' + secs : secs)}</span>`;
      }

      return `
        <tr class="hover:bg-slate-50/80 transition">
          <td class="py-3 px-4 font-mono text-slate-600 font-bold">${inq.tracking_code}</td>
          <td class="py-3 px-4">
            <div class="font-bold text-slate-800">${inq.product_title}</div>
            <div class="text-[11px] text-slate-500 truncate max-w-xs">${inq.user_note || ''}</div>
          </td>
          <td class="py-3 px-4 text-slate-700">${inq.shop_id}</td>
          <td class="py-3 px-4 font-bold text-slate-900">${formatPrice(inq.recorded_price_toman)}</td>
          <td class="py-3 px-4 text-slate-600">${inq.customer_name}</td>
          <td class="py-3 px-4">${remainingDisplay}</td>
          <td class="py-3 px-4">${statusBadge}</td>
          <td class="py-3 px-4 text-slate-400 font-mono text-[11px]">${inq.created_at}</td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    console.error('Failed to load inquiries:', err);
  }
}

// Load stores into dropdown and table
async function loadStores() {
  try {
    const res = await fetch(`${API_BASE}/admin/shops`);
    if (!res.ok) return;
    const shops = await res.json();

    const select = document.getElementById('sim-shop-id');
    select.innerHTML = shops.map(s => `
      <option value="${s.shop_id}">${s.shop_name} (${s.shop_id}) - ${s.is_open ? 'باز' : 'بسته'}</option>
    `).join('');

    const tbody = document.getElementById('stores-table-body');
    if (tbody) {
      tbody.innerHTML = shops.map(s => `
        <tr class="hover:bg-slate-50/80">
          <td class="py-3 px-4 font-mono font-bold text-slate-700">${s.shop_id}</td>
          <td class="py-3 px-4 font-bold text-slate-900">${s.shop_name}</td>
          <td class="py-3 px-4 text-slate-600 max-w-xs truncate">${s.address}</td>
          <td class="py-3 px-4 text-slate-600">${s.phone}</td>
          <td class="py-3 px-4">
            ${s.is_open ? '<span class="text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full text-xs font-bold">دایر و باز</span>' : '<span class="text-rose-700 bg-rose-50 border border-rose-200 px-2.5 py-0.5 rounded-full text-xs font-bold">بسته</span>'}
          </td>
          <td class="py-3 px-4 font-bold text-slate-800">${toPersianDigits(s.active_devices_count || 0)} دستگاه</td>
        </tr>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load shops:', err);
  }
}

// Load Push Notification Logs
async function loadPushLogs() {
  try {
    const res = await fetch(`${API_BASE}/admin/push/logs?limit=50`);
    if (!res.ok) return;
    const logs = await res.json();

    const tbody = document.getElementById('push-logs-table-body');
    if (!logs.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">هنوز لاگ ارسالی ثبت نشده است.</td></tr>`;
      return;
    }

    tbody.innerHTML = logs.map(l => {
      let typeBadge = '';
      if (l.notification_type === 'INITIAL_INQUIRY') {
        typeBadge = '<span class="bg-blue-100 text-blue-800 px-2.5 py-0.5 rounded-full text-[11px] font-bold">ثانیه ۰: استعلام جدید</span>';
      } else if (l.notification_type === 'REMINDER_5MIN') {
        typeBadge = '<span class="bg-amber-100 text-amber-800 px-2.5 py-0.5 rounded-full text-[11px] font-bold">دقیقه ۵: یادآوری</span>';
      } else if (l.notification_type === 'EXPIRATION_ALERT') {
        typeBadge = '<span class="bg-red-100 text-red-800 px-2.5 py-0.5 rounded-full text-[11px] font-bold">دقیقه ۱۰: انقضا</span>';
      } else {
        typeBadge = `<span class="bg-slate-100 text-slate-800 px-2.5 py-0.5 rounded-full text-[11px] font-bold">${l.notification_type}</span>`;
      }

      let statusBadge = '';
      if (l.status === 'DELIVERED') {
        statusBadge = '<span class="text-emerald-600 font-bold">تحویل داده شد (FCM 200)</span>';
      } else if (l.status === 'SIMULATED') {
        statusBadge = '<span class="text-indigo-600 font-bold">شبیه‌سازی و لاگ (Dev Mode)</span>';
      } else {
        statusBadge = `<span class="text-rose-600 font-bold">${l.status}</span>`;
      }

      return `
        <tr class="hover:bg-slate-50/80">
          <td class="py-3 px-4">${typeBadge}</td>
          <td class="py-3 px-4">
            <div class="font-bold text-slate-800">${l.title}</div>
            <div class="text-slate-500 text-[11px]">${l.body}</div>
          </td>
          <td class="py-3 px-4 font-mono text-[11px] text-slate-600">${l.shop_id || '-'}</td>
          <td class="py-3 px-4 font-mono text-[11px] text-slate-500 max-w-[120px] truncate" title="${l.fcm_token || ''}">${l.fcm_token ? l.fcm_token.substring(0, 15) + '...' : '-'}</td>
          <td class="py-3 px-4">${statusBadge}</td>
          <td class="py-3 px-4 text-slate-500 text-[11px] max-w-xs truncate" title="${l.error_detail || ''}">${l.error_detail || '-'}</td>
          <td class="py-3 px-4 font-mono text-slate-400 text-[11px]">${l.dispatched_at}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load push logs:', err);
  }
}

// Load Scheduler settings
async function loadSchedulerConfig() {
  try {
    const res = await fetch(`${API_BASE}/admin/scheduler/config`);
    if (!res.ok) return;
    const cfg = await res.json();
    document.getElementById('cfg-reminder-seconds').value = cfg.reminder_timeout_seconds;
    document.getElementById('cfg-expiration-seconds').value = cfg.expiration_timeout_seconds;
  } catch (err) {
    console.error('Failed to load config:', err);
  }
}

// Update Scheduler settings
async function updateSchedulerConfig(e) {
  e.preventDefault();
  const reminder = parseInt(document.getElementById('cfg-reminder-seconds').value, 10);
  const expiration = parseInt(document.getElementById('cfg-expiration-seconds').value, 10);

  try {
    const res = await fetch(`${API_BASE}/admin/scheduler/config`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        reminder_timeout_seconds: reminder,
        expiration_timeout_seconds: expiration
      })
    });
    if (res.ok) {
      alert('تنظیمات زمان‌بندی با موفقیت ذخیره شد.');
    }
  } catch (err) {
    alert('خطا در ذخیره تنظیمات زمان‌بندی: ' + err);
  }
}

// Submit Test Inquiry
async function submitTestInquiry(e) {
  e.preventDefault();
  const btn = document.getElementById('sim-submit-btn');
  btn.disabled = true;
  btn.innerText = 'در حال ارسال استعلام...';

  const payload = {
    shop_id: document.getElementById('sim-shop-id').value,
    product_title: document.getElementById('sim-product-title').value,
    recorded_price_toman: parseInt(document.getElementById('sim-price').value, 10),
    category_name: document.getElementById('sim-category').value,
    customer_name: document.getElementById('sim-customer-name').value,
    customer_phone: document.getElementById('sim-customer-phone').value,
    user_note: document.getElementById('sim-user-note').value,
    inquiry_type: 'price_and_stock'
  };

  try {
    const res = await fetch(`${API_BASE}/admin/inquiries/create-test`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (res.ok) {
      const alertBox = document.getElementById('sim-success-alert');
      alertBox.classList.remove('hidden');
      setTimeout(() => alertBox.classList.add('hidden'), 5000);
      loadInquiries();
    } else {
      alert('خطا: ' + (data.detail || 'ثبت با شکست مواجه شد'));
    }
  } catch (err) {
    alert('خطای اتصال: ' + err);
  } finally {
    btn.disabled = false;
    btn.innerText = 'ارسال استعلام و فعال‌سازی پوش‌نوتیفیکیشن';
  }
}

function refreshData() {
  loadInquiries();
  loadStores();
  loadPushLogs();
  loadShopChangeRequests();
}

// Fetch and render Shop Change Requests
async function loadShopChangeRequests() {
  const tbody = document.getElementById('change-requests-table-body');
  const badge = document.getElementById('pending-requests-badge');
  try {
    const res = await fetch(`${API_BASE}/admin/shop-change-requests`);
    if (!res.ok) return;
    const requests = await res.json();

    const pendingCount = requests.filter(r => r.status === 'PENDING').length;
    if (badge) {
      if (pendingCount > 0) {
        badge.innerText = toPersianDigits(pendingCount);
        badge.classList.remove('hidden');
      } else {
        badge.classList.add('hidden');
      }
    }

    if (!tbody) return;
    if (!requests.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">هیچ درخواست تغییر اطلاعاتی ثبت نشده است.</td></tr>`;
      return;
    }

    tbody.innerHTML = requests.map(req => {
      let statusBadge = '';
      let actionButtons = '-';

      if (req.status === 'PENDING') {
        statusBadge = `<span class="bg-amber-100 text-amber-800 px-2.5 py-1 rounded-full text-[11px] font-bold">در انتظار بررسی پشتیبانی</span>`;
        actionButtons = `
          <div class="flex items-center gap-1.5">
            <button onclick="approveChangeRequest('${req.request_id}')" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[11px] font-bold transition shadow-sm">
              تایید و اعمال
            </button>
            <button onclick="rejectChangeRequest('${req.request_id}')" class="px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-[11px] font-bold transition shadow-sm">
              رد درخواست
            </button>
          </div>
        `;
      } else if (req.status === 'APPROVED') {
        statusBadge = `<span class="bg-emerald-100 text-emerald-800 px-2.5 py-1 rounded-full text-[11px] font-bold">تایید و اعمال شد</span>`;
        actionButtons = `<span class="text-[11px] text-slate-500">${req.review_notes || 'تایید شد'}</span>`;
      } else if (req.status === 'REJECTED') {
        statusBadge = `<span class="bg-rose-100 text-rose-800 px-2.5 py-1 rounded-full text-[11px] font-bold">رد شد</span>`;
        actionButtons = `<span class="text-[11px] text-rose-600">${req.review_notes || 'رد شد'}</span>`;
      }

      // Changes detail
      let changesHtml = '<div class="space-y-1 text-[11px]">';
      if (req.requested_shop_name) {
        changesHtml += `<div><span class="text-slate-400">نام جدید:</span> <strong class="text-slate-800">${req.requested_shop_name}</strong></div>`;
      }
      if (req.requested_phone) {
        changesHtml += `<div><span class="text-slate-400">تلفن جدید:</span> <span class="font-mono text-slate-800">${toPersianDigits(req.requested_phone)}</span></div>`;
      }
      if (req.requested_address) {
        changesHtml += `<div><span class="text-slate-400">آدرس جدید:</span> <span class="text-slate-800">${req.requested_address}</span></div>`;
      }
      if (req.requested_open_time || req.requested_close_time) {
        changesHtml += `<div><span class="text-slate-400">ساعت کاری:</span> <span class="font-mono text-slate-800">${toPersianDigits(req.requested_open_time || '')} تا ${toPersianDigits(req.requested_close_time || '')}</span></div>`;
      }
      changesHtml += '</div>';

      return `
        <tr class="hover:bg-slate-50/80 transition">
          <td class="py-3 px-4 font-mono text-slate-600 font-bold text-[11px]">${req.request_id}</td>
          <td class="py-3 px-4 text-slate-700 font-mono text-[11px]">${req.shop_id}</td>
          <td class="py-3 px-4">${changesHtml}</td>
          <td class="py-3 px-4 text-slate-600 max-w-xs text-[11px]">${req.reason || 'بدون توضیح'}</td>
          <td class="py-3 px-4">${statusBadge}</td>
          <td class="py-3 px-4 text-slate-400 font-mono text-[11px]">${req.created_at}</td>
          <td class="py-3 px-4">${actionButtons}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-rose-500">خطا در دریافت لیست درخواست‌ها</td></tr>`;
  }
}

async function approveChangeRequest(requestId) {
  if (!confirm('آیا از تایید این درخواست و اعمال مستقیم مشخصات در فروشگاه اطمینان دارید؟')) return;
  try {
    const res = await fetch(`${API_BASE}/admin/shop-change-requests/${requestId}/approve`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ action: 'approve', review_notes: 'تایید توسط پشتیبانی ترب' })
    });
    if (res.ok) {
      alert('درخواست با موفقیت تایید و مشخصات فروشگاه بروزرسانی شد.');
      loadShopChangeRequests();
      loadStores();
    } else {
      const err = await res.json();
      alert('خطا: ' + (err.detail || 'تایید ناموفق'));
    }
  } catch (err) {
    alert('خطای اتصال: ' + err);
  }
}

async function rejectChangeRequest(requestId) {
  const reason = prompt('علت رد درخواست را جهت اطلاع فروشنده وارد کنید:');
  if (reason === null) return;
  try {
    const res = await fetch(`${API_BASE}/admin/shop-change-requests/${requestId}/reject`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ action: 'reject', review_notes: reason || 'رد توسط پشتیبانی ترب' })
    });
    if (res.ok) {
      alert('درخواست رد شد.');
      loadShopChangeRequests();
    } else {
      const err = await res.json();
      alert('خطا: ' + (err.detail || 'رد ناموفق'));
    }
  } catch (err) {
    alert('خطای اتصال: ' + err);
  }
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
  loadInquiries();
  loadStores();
  loadShopChangeRequests();
  setInterval(loadInquiries, 5000); // 5s auto-refresh
  setInterval(loadShopChangeRequests, 10000); // 10s auto-refresh
});
