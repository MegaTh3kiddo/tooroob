import { Product, Store, Inquiry, PlanStop } from '../types';
import { PRODUCTS, STORES, CATS } from '../data/mockData';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T | null> {
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Edge': 'Next-Frontend',
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
    if (!res.ok) {
      console.warn(`[API] ${options?.method || 'GET'} ${url} returned ${res.status}`);
      return null;
    }
    return (await res.json()) as T;
  } catch (err) {
    console.warn(`[API] Error contacting ${url}:`, err);
    return null;
  }
}

export const TorobApi = {
  // Check backend health
  async checkHealth(): Promise<{ status: string; catalog_counts: any } | null> {
    return await fetchJson(`${BASE_URL}/health`);
  },

  // Search products
  async searchProducts(q?: string, category?: string, brand?: string): Promise<{ items: Product[]; total: number }> {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (category) params.set('category', category);
    if (brand) params.set('brand', brand);

    const data = await fetchJson<{ items: any[]; total: number }>(`${BASE_URL}/products?${params.toString()}`);
    if (data && data.items) {
      return {
        items: data.items.map((it) => ({
          id: it.id,
          brand: it.brand || '',
          title: it.title || it.model || it.id,
          tagline: it.description || '',
          desc: it.description || '',
          specs: Object.entries(it.specs || {}).map(([k, v]) => [k, String(v)]),
          colors: it.colors || ['مشکی', 'سفید'],
        })),
        total: data.total,
      };
    }

    // Fallback to local mock catalog
    const all = Object.values(PRODUCTS).flat();
    const filtered = all.filter((p) => {
      if (q && !p.title.toLowerCase().includes(q.toLowerCase()) && !p.brand.toLowerCase().includes(q.toLowerCase())) {
        return false;
      }
      return true;
    });

    return { items: filtered, total: filtered.length };
  },

  // Assistant / TorobChat
  async createSession(initialMessage?: string): Promise<string> {
    const res = await fetchJson<{ session_id: string }>(`${BASE_URL}/assistant/sessions`, {
      method: 'POST',
      body: JSON.stringify({ initial_message: initialMessage }),
    });
    return res?.session_id || `session_${Date.now()}`;
  },

  async sendMessage(
    sessionId: string,
    message: string,
    userId?: string
  ): Promise<{
    reply_text: string;
    detected_intent?: string;
    recommendations?: any;
    proposed_actions?: any[];
  }> {
    const res = await fetchJson<any>(`${BASE_URL}/assistant/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ message, user_id: userId }),
    });

    if (res && res.reply_text) {
      return res;
    }

    // Fallback simulation
    return {
      reply_text: `در حال بررسی پرسش شما («${message}»)... بهترین گزینه‌ها را در فروشگاه‌های تهران برای شما فهرست کردم.`,
      detected_intent: 'general_shopping',
      proposed_actions: [],
    };
  },

  // Inquiries
  async listInquiries(): Promise<Inquiry[]> {
    const res = await fetchJson<{ items: any[] }>(`${BASE_URL}/inquiries`);
    if (res && res.items) {
      return res.items.map((i) => ({
        id: i.id,
        shop_id: i.shop_id,
        shop_name: STORES[i.shop_id]?.name || 'فروشگاه',
        product_id: i.product_id,
        status: i.status || 'pending',
        question: i.question_scope?.type === 'price_and_stock' ? 'استعلام قیمت و موجودی' : 'استعلام کالا',
        created_at: i.created_at || new Date().toISOString(),
      }));
    }
    return [];
  },

  async createInquiry(shopId: string, productId?: string, offerId?: string): Promise<Inquiry> {
    const payload = {
      shop_id: shopId,
      product_id: productId,
      offer_id: offerId,
      question_scope: { type: 'price_and_stock' },
      priority: 'medium',
    };
    const res = await fetchJson<any>(`${BASE_URL}/inquiries`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    return {
      id: res?.inquiry?.id || `inq_${Date.now()}`,
      shop_id: shopId,
      shop_name: STORES[shopId]?.name || 'فروشگاه',
      product_id: productId,
      status: 'pending',
      question: 'استعلام قیمت و موجودی روز',
      created_at: new Date().toISOString(),
    };
  },

  async submitFeedback(
    shopId: string,
    issueType: string,
    notes?: string,
    offerId?: string,
    productId?: string
  ): Promise<boolean> {
    const res = await fetchJson<any>(`${BASE_URL}/feedback/cases`, {
      method: 'POST',
      body: JSON.stringify({
        shop_id: shopId,
        issue_type: issueType,
        notes: notes || '',
        offer_id: offerId,
        product_id: productId,
      }),
    });
    return !!res;
  },

  // Routing and Itinerary Planning
  async planRoute(
    originLat: number,
    originLon: number,
    stops: { shop_id: string; product_ids: string[] }[],
    sortMode: string = 'smart'
  ): Promise<any> {
    const res = await fetchJson<any>(`${BASE_URL}/plans/route`, {
      method: 'POST',
      body: JSON.stringify({
        origin_lat: originLat,
        origin_lon: originLon,
        stops,
        sort_mode: sortMode,
        dwell_minutes_per_stop: 10,
      }),
    });
    return res;
  },
};
