import { LatLng, TravelMode, PlanStop } from '../types';
import { STORES } from '../data/mockData';

export const DEF_TRAVEL = {
  walk: { label: 'پیاده', base: 0, perKm: 12, maxKm: 3 },
  transit: { label: 'اتوبوس یا مترو', base: 14, perKm: 1.9, maxKm: Infinity },
  car: { label: 'ماشین', base: 4, perKm: 2.7, maxKm: Infinity },
  moto: { label: 'موتور', base: 3, perKm: 2.2, maxKm: Infinity },
};

export function distanceKm(a: LatLng, b: LatLng): number {
  const R = 6371; // Earth radius in km
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const lat1 = (a.lat * Math.PI) / 180;
  const lat2 = (b.lat * Math.PI) / 180;

  const sinDLat = Math.sin(dLat / 2);
  const sinDLng = Math.sin(dLng / 2);

  const aVal = sinDLat * sinDLat + Math.cos(lat1) * Math.cos(lat2) * sinDLng * sinDLng;
  const c = 2 * Math.atan2(Math.sqrt(aVal), Math.sqrt(1 - aVal));
  return R * c;
}

export function roadKm(a: LatLng, b: LatLng): number {
  return distanceKm(a, b) * 1.3;
}

export function travelMinutes(mode: keyof typeof DEF_TRAVEL, km: number): number {
  const d = DEF_TRAVEL[mode] || DEF_TRAVEL.car;
  return Math.max(1, Math.round(d.base + km * d.perKm));
}

export function suggestMode(km: number): 'walk' | 'transit' | 'car' {
  const order: ('walk' | 'transit' | 'car')[] = ['walk', 'transit', 'car'];
  const candidates = order.filter((m) => km <= DEF_TRAVEL[m].maxKm);
  const minTime = Math.min(...candidates.map((m) => travelMinutes(m, km)));
  const tol = Math.max(4, minTime * 0.25);
  for (const m of candidates) {
    if (travelMinutes(m, km) <= minTime + tol) return m;
  }
  return 'car';
}

export function resolveMode(mode: TravelMode, km: number): 'walk' | 'transit' | 'car' | 'moto' {
  if (mode === 'auto') return suggestMode(km);
  return mode;
}

export interface ScheduledStop {
  stop: PlanStop;
  storeName: string;
  km: number;
  travelMin: number;
  arriveTime: number; // minutes from midnight
  status: 'open' | 'soon' | 'later' | 'closed';
  openH: number;
  closeH: number;
}

export function calculateSchedule(
  origin: LatLng,
  stops: PlanStop[],
  mode: TravelMode = 'auto',
  startMinutes?: number
): {
  rows: ScheduledStop[];
  totalKm: number;
  totalMinutes: number;
  warnings: number;
} {
  const now = new Date();
  const start = startMinutes ?? now.getHours() * 60 + now.getMinutes();
  let t = start;
  let pos = origin;
  let totalKm = 0;
  let warnings = 0;

  const rows: ScheduledStop[] = [];

  for (const stop of stops) {
    const store = STORES[stop.sid];
    if (!store) continue;

    const km = roadKm(pos, { lat: store.lat, lng: store.lng });
    const resolved = resolveMode(mode, km);
    const tm = travelMinutes(resolved, km);
    const arrive = t + tm;

    const openMin = store.openH * 60;
    const closeMin = store.closeH * 60;

    let status: 'open' | 'soon' | 'later' | 'closed' = 'open';
    if (arrive >= closeMin) {
      status = 'closed';
      warnings++;
    } else if (arrive < openMin) {
      status = 'later';
      warnings++;
    } else if (closeMin - arrive <= 60) {
      status = 'soon';
    }

    rows.push({
      stop,
      storeName: store.name,
      km,
      travelMin: tm,
      arriveTime: arrive,
      status,
      openH: store.openH,
      closeH: store.closeH,
    });

    totalKm += km;
    t = status === 'closed' ? arrive : Math.max(arrive, openMin) + 10; // 10 min dwell
    pos = { lat: store.lat, lng: store.lng };
  }

  return {
    rows,
    totalKm,
    totalMinutes: t - start,
    warnings,
  };
}
