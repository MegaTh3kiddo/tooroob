'use client';

import { useEffect } from 'react';

// Load order matters: the reference scripts share the global NQ namespace.
const SCRIPTS = [
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  '/js/data.js',
  '/js/icons.js',
  '/js/travel.js',
  '/js/art.js',
  '/js/cluster.js',
  '/js/map.js',
  '/js/plan.js',
  '/js/agent.js',
  '/js/account.js',
  '/js/app.js',
  '/js/catalog.js',
  '/js/backend.js',
];

let started = false;

export function UiScripts() {
  useEffect(() => {
    if (started) return;
    started = true;
    (async () => {
      for (const src of SCRIPTS) {
        await new Promise<void>((resolve) => {
          const s = document.createElement('script');
          s.src = src;
          s.async = false;
          s.onload = () => resolve();
          s.onerror = () => { console.warn('[ui] failed to load', src); resolve(); };
          document.body.appendChild(s);
        });
      }
    })();
  }, []);
  return null;
}
