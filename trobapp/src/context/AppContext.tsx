'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  ViewMode,
  City,
  Product,
  Category,
  FilterState,
  PlanStop,
  TravelMode,
  Inquiry,
  ModalType,
  ChatMessage,
  Offer,
} from '../types';
import { CITIES, CATS, PRODUCTS, STORES, OFFERS, ORIGIN } from '../data/mockData';
import { TorobApi } from '../services/api';

interface CompareSlots {
  a: { offer: Offer; product?: Product; storeName: string } | null;
  b: { offer: Offer; product?: Product; storeName: string } | null;
}

const DEFAULT_FILTERS: FilterState = {
  minPrice: 0,
  maxPrice: 150000000,
  torobpayOnly: false,
  guaranteeOnly: false,
  installmentsOnly: false,
  inStockOnly: false,
  openNowOnly: false,
  minRating: 0,
  fastOnly: false,
  maxDistance: 50,
  sort: 'smart',
};

interface AppContextType {
  view: ViewMode;
  setView: (v: ViewMode) => void;
  city: City;
  setCity: (c: City) => void;
  cities: City[];
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  activeCategory: Category;
  setActiveCategory: (cat: Category) => void;
  selectedProduct: Product | null;
  setSelectedProduct: (p: Product | null) => void;
  filters: FilterState;
  setFilters: React.Dispatch<React.SetStateAction<FilterState>>;
  resetFilters: () => void;
  compareSlots: CompareSlots;
  setCompareSlot: (slot: 'a' | 'b', data: any) => void;
  clearCompareSlot: (slot: 'a' | 'b') => void;
  planStops: PlanStop[];
  togglePlanStop: (sid: string, catId?: string) => boolean;
  removePlanStop: (sid: string) => void;
  clearPlan: () => void;
  setStopDone: (sid: string, done: boolean) => void;
  movePlanStop: (sid: string, dir: -1 | 1) => void;
  travelMode: TravelMode;
  setTravelMode: (m: TravelMode) => void;
  inquiries: Inquiry[];
  addInquiry: (shopId: string, productId?: string) => Promise<void>;
  activeModal: ModalType;
  modalData: any;
  openModal: (type: ModalType, data?: any) => void;
  closeModal: () => void;
  isTopCollapsed: boolean;
  setIsTopCollapsed: React.Dispatch<React.SetStateAction<boolean>>;
  isHistOpen: boolean;
  setIsHistOpen: React.Dispatch<React.SetStateAction<boolean>>;
  isVisitsOpen: boolean;
  setIsVisitsOpen: React.Dispatch<React.SetStateAction<boolean>>;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  user: { phone?: string; isLoggedIn: boolean };
  login: (phone: string) => void;
  logout: () => void;
  chatMessages: ChatMessage[];
  sendChatMessage: (text: string) => Promise<void>;
  clearChat: () => void;
  selectedStoreForMap: string | null;
  setSelectedStoreForMap: (sid: string | null) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [view, setView] = useState<ViewMode>('list');
  const [city, setCity] = useState<City>(CITIES[0]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeCategory, setActiveCategory] = useState<Category>(CATS[0]);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(PRODUCTS['headphone']?.[0] || null);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  const [compareSlots, setCompareSlots] = useState<CompareSlots>({ a: null, b: null });
  const [planStops, setPlanStops] = useState<PlanStop[]>([]);
  const [travelMode, setTravelMode] = useState<TravelMode>('auto');

  const [inquiries, setInquiries] = useState<Inquiry[]>([
    {
      id: 'iq_init1',
      shop_id: 's1',
      shop_name: 'آوا دیجیتال',
      product_id: 'aura520',
      product_title: 'هدفون Aura 520',
      status: 'answered',
      question: 'استعلام قیمت و موجودی روز',
      created_at: new Date(Date.now() - 3600000).toISOString(),
      answer: {
        confirmed_price: 3890000,
        in_stock: true,
        shop_is_open: true,
        notes: 'موجود در رنگ مشکی و سرمه‌ای با گارانتی ۱۸ ماهه اصلی',
        answered_at: new Date(Date.now() - 1800000).toISOString(),
      },
    },
  ]);

  const [activeModal, setActiveModal] = useState<ModalType>(null);
  const [modalData, setModalData] = useState<any>(null);

  const [isTopCollapsed, setIsTopCollapsed] = useState<boolean>(false);
  const [isHistOpen, setIsHistOpen] = useState<boolean>(false);
  const [isVisitsOpen, setIsVisitsOpen] = useState<boolean>(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  const [user, setUser] = useState<{ phone?: string; isLoggedIn: boolean }>({ isLoggedIn: false });
  const [selectedStoreForMap, setSelectedStoreForMap] = useState<string | null>(null);

  // Assistant messages state
  const [chatSessionId, setChatSessionId] = useState<string>('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: 'm1',
      sender: 'agent',
      text: 'سلام! دستیار خرید هوشمند ترب هستم. چطور می‌تونم به شما در انتخاب و خرید نزدیک‌ترین کالا کمک کنم؟',
      timestamp: Date.now(),
      chips: [
        'گوشی تا ۳۰ میلیون چی بخرم؟',
        'نزدیک‌ترین فروشگاه با تخفیف کجاست؟',
        'هدفون با نویز کنسلینگ عالی',
        'خرید قسطی لپ‌تاپ با ترب‌پی',
      ],
    },
  ]);

  // Load saved state from localStorage
  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem('nq-theme');
      if (savedTheme === 'dark' || savedTheme === 'light') {
        setTheme(savedTheme);
        document.documentElement.setAttribute('data-theme', savedTheme);
      }
      const savedPlan = localStorage.getItem('nq-plan-v1');
      if (savedPlan) {
        const parsed = JSON.parse(savedPlan);
        if (parsed.stops) setPlanStops(parsed.stops);
      }
      const savedTravel = localStorage.getItem('nq-travel-v1');
      if (savedTravel) setTravelMode(savedTravel as TravelMode);
    } catch (e) {
      console.warn('LocalStorage error:', e);
    }
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
    try {
      localStorage.setItem('nq-theme', nextTheme);
    } catch (e) {}
  };

  const resetFilters = () => setFilters(DEFAULT_FILTERS);

  const setCompareSlot = (slot: 'a' | 'b', data: any) => {
    setCompareSlots((prev) => ({ ...prev, [slot]: data }));
  };

  const clearCompareSlot = (slot: 'a' | 'b') => {
    setCompareSlots((prev) => ({ ...prev, [slot]: null }));
  };

  const togglePlanStop = (sid: string, catId?: string): boolean => {
    const cat = catId || activeCategory.id;
    let added = false;
    setPlanStops((prev) => {
      const existing = prev.find((s) => s.sid === sid);
      let next: PlanStop[];
      if (!existing) {
        next = [...prev, { sid, cats: [cat], done: false }];
        added = true;
      } else {
        const catIdx = existing.cats.indexOf(cat);
        if (catIdx > -1) {
          const nextCats = existing.cats.filter((c) => c !== cat);
          if (nextCats.length === 0) {
            next = prev.filter((s) => s.sid !== sid);
          } else {
            next = prev.map((s) => (s.sid === sid ? { ...s, cats: nextCats } : s));
          }
        } else {
          next = prev.map((s) => (s.sid === sid ? { ...s, cats: [...s.cats, cat] } : s));
          added = true;
        }
      }
      try {
        localStorage.setItem('nq-plan-v1', JSON.stringify({ stops: next }));
      } catch (e) {}
      return next;
    });
    return added;
  };

  const removePlanStop = (sid: string) => {
    setPlanStops((prev) => {
      const next = prev.filter((s) => s.sid !== sid);
      try {
        localStorage.setItem('nq-plan-v1', JSON.stringify({ stops: next }));
      } catch (e) {}
      return next;
    });
  };

  const clearPlan = () => {
    setPlanStops([]);
    try {
      localStorage.setItem('nq-plan-v1', JSON.stringify({ stops: [] }));
    } catch (e) {}
  };

  const setStopDone = (sid: string, done: boolean) => {
    setPlanStops((prev) => {
      const item = prev.find((s) => s.sid === sid);
      if (!item) return prev;
      const updated = { ...item, done };
      const rest = prev.filter((s) => s.sid !== sid);
      const next = done ? [...rest, updated] : [updated, ...rest];
      try {
        localStorage.setItem('nq-plan-v1', JSON.stringify({ stops: next }));
      } catch (e) {}
      return next;
    });
  };

  const movePlanStop = (sid: string, dir: -1 | 1) => {
    setPlanStops((prev) => {
      const idx = prev.findIndex((s) => s.sid === sid);
      const targetIdx = idx + dir;
      if (idx < 0 || targetIdx < 0 || targetIdx >= prev.length) return prev;
      const copy = [...prev];
      const temp = copy[idx];
      copy[idx] = copy[targetIdx];
      copy[targetIdx] = temp;
      try {
        localStorage.setItem('nq-plan-v1', JSON.stringify({ stops: copy }));
      } catch (e) {}
      return copy;
    });
  };

  const openModal = (type: ModalType, data?: any) => {
    setActiveModal(type);
    setModalData(data || null);
  };

  const closeModal = () => {
    setActiveModal(null);
    setModalData(null);
  };

  const addInquiry = async (shopId: string, productId?: string) => {
    const newInq = await TorobApi.createInquiry(shopId, productId);
    setInquiries((prev) => [newInq, ...prev]);
  };

  const login = (phone: string) => {
    setUser({ phone, isLoggedIn: true });
    closeModal();
  };

  const logout = () => {
    setUser({ isLoggedIn: false });
  };

  const sendChatMessage = async (text: string) => {
    const userMsg: ChatMessage = {
      id: `u_${Date.now()}`,
      sender: 'user',
      text,
      timestamp: Date.now(),
    };
    setChatMessages((prev) => [...prev, userMsg]);

    let sid = chatSessionId;
    if (!sid) {
      sid = await TorobApi.createSession(text);
      setChatSessionId(sid);
    }

    const res = await TorobApi.sendMessage(sid, text, user.phone);
    const agentMsg: ChatMessage = {
      id: `a_${Date.now()}`,
      sender: 'agent',
      text: res.reply_text,
      timestamp: Date.now(),
      cards: [],
      chips: ['مشاهده روی نقشه', 'فیلتر بر اساس ارزان‌ترین', 'ثبت در برنامه سر زدن'],
    };

    // If query mentions products or categories, attach rich cards
    if (text.includes('هدفون') || text.includes('Aura') || text.includes('نویز')) {
      agentMsg.cards = [
        {
          type: 'product',
          data: PRODUCTS['headphone']?.[0],
        },
      ];
    }

    setChatMessages((prev) => [...prev, agentMsg]);
  };

  const clearChat = () => {
    setChatMessages([
      {
        id: 'm1',
        sender: 'agent',
        text: 'گفتگوی جدید آغاز شد. چطور می‌توانم راهنمایی‌تان کنم؟',
        timestamp: Date.now(),
        chips: ['بهترین قیمت گوشی', 'فروشگاه‌های باز در تهران', 'خرید اقساطی'],
      },
    ]);
  };

  return (
    <AppContext.Provider
      value={{
        view,
        setView,
        city,
        setCity,
        cities: CITIES,
        searchQuery,
        setSearchQuery,
        activeCategory,
        setActiveCategory,
        selectedProduct,
        setSelectedProduct,
        filters,
        setFilters,
        resetFilters,
        compareSlots,
        setCompareSlot,
        clearCompareSlot,
        planStops,
        togglePlanStop,
        removePlanStop,
        clearPlan,
        setStopDone,
        movePlanStop,
        travelMode,
        setTravelMode,
        inquiries,
        addInquiry,
        activeModal,
        modalData,
        openModal,
        closeModal,
        isTopCollapsed,
        setIsTopCollapsed,
        isHistOpen,
        setIsHistOpen,
        isVisitsOpen,
        setIsVisitsOpen,
        theme,
        toggleTheme,
        user,
        login,
        logout,
        chatMessages,
        sendChatMessage,
        clearChat,
        selectedStoreForMap,
        setSelectedStoreForMap,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within an AppProvider');
  return ctx;
};
