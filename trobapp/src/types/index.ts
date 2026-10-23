export type ViewMode = 'agent' | 'list' | 'map' | 'inqs';

export interface LatLng {
  lat: number;
  lng: number;
}

export interface City {
  id: string;
  name: string;
  active: boolean;
  center?: LatLng;
}

export interface StoreInstallment {
  t: 'digipay' | 'loan' | 'torobpay';
  terms: string;
}

export interface Store {
  id?: string;
  name: string;
  lat: number;
  lng: number;
  addr: string;
  hours: string;
  openH: number;
  closeH: number;
  phone: string;
  phones?: string[];
  torobpay: boolean;
  installments?: StoreInstallment[];
  rating: number;
  years: number;
  orders90: string;
  followups: number;
  guarantee?: boolean;
  fast?: string;
  instagram?: string;
  website?: string;
  messenger?: 'whatsapp' | 'bale';
  bale?: string;
  inquiry?: boolean;
  [key: string]: any;
}

export interface Product {
  id: string;
  brand: string;
  title: string;
  kind?: string;
  tagline?: string;
  desc?: string;
  specs: [string, string][];
  colors?: string[];
  image?: string;
  more?: [string, string][];
  [key: string]: any;
}

export interface Category {
  id: string;
  name: string;
  words: string[];
  food?: boolean;
  [key: string]: any;
}

export interface Offer {
  storeId: string;
  price: number;
  color?: string;
  warranty?: string;
  updatedHoursAgo: number;
  stock?: 'in' | 'unsure' | 'out';
  fast?: boolean;
  [key: string]: any;
}

export interface Inquiry {
  id: string;
  shop_id: string;
  shop_name: string;
  product_id?: string;
  product_title?: string;
  status: 'pending' | 'answered' | 'expired' | 'canceled';
  question: string;
  created_at: string;
  answer?: {
    confirmed_price?: number;
    in_stock?: boolean;
    shop_is_open?: boolean;
    notes?: string;
    answered_at?: string;
  };
}

export interface PlanStop {
  sid: string;
  cats: string[];
  done?: boolean;
}

export type TravelMode = 'auto' | 'walk' | 'transit' | 'car' | 'moto';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: number;
  cards?: {
    type: 'product' | 'offer' | 'store' | 'compare' | 'area';
    data: any;
  }[];
  chips?: string[];
}

export interface FilterState {
  minPrice: number;
  maxPrice: number;
  torobpayOnly: boolean;
  guaranteeOnly: boolean;
  installmentsOnly: boolean;
  inStockOnly: boolean;
  openNowOnly: boolean;
  minRating: number;
  fastOnly: boolean;
  maxDistance: number;
  sort: 'smart' | 'priceAsc' | 'distAsc' | 'ratingDesc' | 'fast';
}

export type ModalType =
  | 'filter'
  | 'help'
  | 'call'
  | 'spec'
  | 'cmp'
  | 'gallery'
  | 'report'
  | 'store'
  | 'account'
  | null;
