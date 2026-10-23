// Vector Artwork & Fallback Illustrations from static-ui-ref/js/art.js
const L = 'stroke="currentColor" stroke-width="2.4"';

function svg(inner: string): string {
  return (
    '<svg viewBox="0 0 96 96" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
    '<ellipse cx="48" cy="87" rx="24" ry="3.4" fill="currentColor" opacity=".08"/>' +
    inner +
    '</svg>'
  );
}

function keys(cols: number, rows: number, x0: number, y0: number, px: number, py: number, w: number, h: number): string {
  let s = '';
  for (let r = 0; r < rows; r++) {
    for (let col = 0; col < cols; col++) {
      s += '<rect x="' + (x0 + col * px) + '" y="' + (y0 + r * py) + '" width="' + w + '" height="' + h + '" rx="1.2" fill="currentColor" opacity=".22"/>';
    }
  }
  return s;
}

const A: Record<string, (c: string) => string> = {
  over: (c: string) => {
    const band = 'M24 58V46a24 24 0 0 1 48 0v12';
    return (
      '<path d="' + band + '" stroke="currentColor" stroke-width="9"/><path d="' + band + '" stroke="' + c + '" stroke-width="5"/>' +
      '<rect x="13" y="50" width="20" height="32" rx="10" fill="' + c + '" ' + L + '/><rect x="63" y="50" width="20" height="32" rx="10" fill="' + c + '" ' + L + '/>' +
      '<rect x="17" y="59" width="6" height="14" rx="3" fill="currentColor" opacity=".22"/><rect x="73" y="59" width="6" height="14" rx="3" fill="currentColor" opacity=".22"/>'
    );
  },
  buds: (c: string) => {
    return (
      '<rect x="40" y="32" width="7" height="24" rx="3.5" fill="' + c + '" ' + L + '/><rect x="49" y="32" width="7" height="24" rx="3.5" fill="' + c + '" ' + L + '/>' +
      '<circle cx="36" cy="30" r="10" fill="' + c + '" ' + L + '/><circle cx="60" cy="30" r="10" fill="' + c + '" ' + L + '/>' +
      '<rect x="20" y="54" width="56" height="30" rx="15" fill="' + c + '" ' + L + '/><path d="M22 66h52" stroke="currentColor" stroke-width="1.8" opacity=".35"/>' +
      '<circle cx="48" cy="75" r="2.2" fill="currentColor" opacity=".55"/>'
    );
  },
  kb75: (c: string) => {
    return (
      '<rect x="8" y="28" width="80" height="42" rx="7" fill="' + c + '" ' + L + '/>' +
      keys(11, 3, 13, 33, 6.6, 7.2, 5, 4.8) +
      keys(3, 1, 13, 54.6, 6.6, 7.2, 5, 4.8) +
      '<rect x="32.8" y="54.6" width="31.4" height="4.8" rx="1.2" fill="currentColor" opacity=".22"/>' +
      keys(3, 1, 65.8, 54.6, 6.6, 7.2, 5, 4.8)
    );
  },
  tkl: (c: string) => {
    return (
      '<rect x="6" y="24" width="84" height="48" rx="7" fill="' + c + '" ' + L + '/>' +
      keys(13, 4, 11, 29, 5.9, 6.6, 4.3, 4.4) +
      keys(3, 1, 11, 55.4, 5.9, 6.6, 4.3, 4.4) +
      '<rect x="30" y="55.4" width="29" height="4.4" rx="1.2" fill="currentColor" opacity=".22"/>' +
      keys(4, 1, 64.1, 55.4, 5.9, 6.6, 4.3, 4.4)
    );
  },
  gan: (c: string) => {
    return (
      '<rect x="38" y="14" width="5" height="16" rx="1.6" fill="currentColor" opacity=".8"/><rect x="53" y="14" width="5" height="16" rx="1.6" fill="currentColor" opacity=".8"/>' +
      '<rect x="24" y="28" width="48" height="54" rx="12" fill="' + c + '" ' + L + '/><path d="M38 42h20" stroke="currentColor" stroke-width="3" opacity=".25"/>' +
      '<rect x="40" y="58" width="16" height="8" rx="4" fill="currentColor" opacity=".7"/><circle cx="62" cy="38" r="2" fill="currentColor" opacity=".5"/>'
    );
  },
  dual: (c: string) => {
    return (
      '<rect x="37" y="14" width="5" height="16" rx="1.6" fill="currentColor" opacity=".8"/><rect x="54" y="14" width="5" height="16" rx="1.6" fill="currentColor" opacity=".8"/>' +
      '<rect x="20" y="28" width="56" height="54" rx="12" fill="' + c + '" ' + L + '/><path d="M34 42h28" stroke="currentColor" stroke-width="3" opacity=".25"/>' +
      '<rect x="32" y="58" width="14" height="8" rx="4" fill="currentColor" opacity=".7"/><rect x="50" y="58" width="14" height="8" rx="2" fill="currentColor" opacity=".7"/>'
    );
  },
  bank: (c: string) => {
    return (
      '<rect x="29" y="10" width="38" height="76" rx="11" fill="' + c + '" ' + L + '/>' +
      [22, 29, 36, 43].map((y) => '<rect x="39" y="' + y + '" width="18" height="3.6" rx="1.8" fill="currentColor" opacity=".45"/>').join('') +
      '<rect x="41" y="73" width="14" height="5" rx="2.5" fill="currentColor" opacity=".6"/>'
    );
  },
  nano: (c: string) => {
    return (
      '<rect x="31" y="16" width="34" height="66" rx="9" fill="' + c + '" ' + L + '/><rect x="38" y="25" width="20" height="11" rx="3" fill="currentColor" opacity=".25"/>' +
      '<path d="M42 30h12" stroke="currentColor" stroke-width="2" opacity=".6"/><rect x="42" y="70" width="12" height="5" rx="2.5" fill="currentColor" opacity=".6"/>'
    );
  },
  raze: (c: string) => {
    return (
      '<path d="M48 12c-15 0-24 18-24 40 0 16 10 28 24 28s24-12 24-28c0-22-9-40-24-40z" fill="' + c + '" ' + L + '/>' +
      '<path d="M48 12v30M38 32h20" stroke="currentColor" stroke-width="2" opacity=".5"/>' +
      '<circle cx="48" cy="24" r="3" fill="currentColor" opacity=".7"/><path d="M32 46h32" stroke="currentColor" stroke-width="1.8" opacity=".35"/>'
    );
  },
  viper: (c: string) => {
    return (
      '<path d="M48 10c-14 0-22 17-22 38 0 18 9 32 22 32s22-14 22-32c0-21-8-38-22-38z" fill="' + c + '" ' + L + '/>' +
      '<path d="M48 10v28M39 30h18" stroke="currentColor" stroke-width="2" opacity=".5"/>' +
      '<rect x="46" y="20" width="4" height="9" rx="2" fill="currentColor" opacity=".7"/>'
    );
  },
  laptop: (c: string) => {
    return (
      '<rect x="20" y="22" width="56" height="38" rx="4" fill="' + c + '" ' + L + '/><rect x="25" y="27" width="46" height="28" rx="2" fill="currentColor" opacity=".18"/>' +
      '<path d="M12 64h72l-5 9H17z" fill="' + c + '" ' + L + '/><path d="M42 68h12" stroke="currentColor" stroke-width="2" opacity=".4"/>'
    );
  },
  box: (c: string) => {
    return (
      '<path d="M20 34l28-12 28 12v32L48 78 20 66z" fill="' + c + '" ' + L + '/><path d="M20 34l28 12 28-12M48 46v32" ' + L + '/>' +
      '<path d="M34 28l28 12v9" stroke="currentColor" stroke-width="2" opacity=".45"/><rect x="26" y="50" width="14" height="8" rx="1.5" transform="skewY(23)" fill="currentColor" opacity=".18"/>'
    );
  },
  rice: (c: string) => {
    c = c || '#E9DFC7';
    return (
      '<path d="M28 24h40l4 8-2 44a6 6 0 0 1-6 6H32a6 6 0 0 1-6-6l-2-44z" fill="#F3EBD8" ' + L + '/><path d="M28 24c6 4 34 4 40 0" ' + L + '/>' +
      '<rect x="32" y="40" width="32" height="22" rx="4" fill="' + c + '" opacity=".9"/><path d="M38 51h20M42 56h12" stroke="#fff" stroke-width="2.4"/>' +
      '<path d="M40 46c3-3 6 3 9 0s6 3 9 0" stroke="#fff" stroke-width="1.8"/>'
    );
  },
  grain: () => {
    let g = '';
    [[34,46,20],[42,42,-15],[50,45,30],[58,42,-25],[38,52,-30],[46,50,10],[54,52,-10],[62,49,25],[44,38,40],[52,37,-35]].forEach((d) => {
      g += '<ellipse cx="' + d[0] + '" cy="' + d[1] + '" rx="4.6" ry="1.9" transform="rotate(' + d[2] + ' ' + d[0] + ' ' + d[1] + ')" fill="#FBF7EC" stroke="currentColor" stroke-width="1.2"/>';
    });
    return (
      '<path d="M16 50h64a32 26 0 0 1-64 0z" fill="#C9A27A" ' + L + '/><path d="M20 50c8-16 48-16 56 0" fill="#FBF7EC" ' + L + '/>' + g
    );
  }
};

export function getProductArt(kind: string, color: string = '#8C9692'): string {
  const fn = A[kind] || A.over;
  return svg(fn(color));
}

const BRC = [
  ['#1D4ED8', '#60A5FA'],
  ['#7C3AED', '#C084FC'],
  ['#047857', '#34D399'],
  ['#B45309', '#FBBF24'],
  ['#BE185D', '#F472B6'],
  ['#0E7490', '#22D3EE'],
  ['#B91C1C', '#F87171'],
  ['#374151', '#9CA3AF'],
];

export function getBrandLogo(name: string): string {
  let h = 0;
  String(name).split('').forEach((ch) => {
    h = (h * 33 + ch.charCodeAt(0)) >>> 0;
  });
  const c = BRC[h % BRC.length];
  const id = 'bg' + (h % 100000);
  const ch = String(name).trim().charAt(0).toUpperCase();
  return (
    '<svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><defs><linearGradient id="' +
    id +
    '" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="' +
    c[0] +
    '"/><stop offset="1" stop-color="' +
    c[1] +
    '"/></linearGradient></defs>' +
    '<rect width="64" height="64" rx="16" fill="url(#' +
    id +
    ')"/><circle cx="50" cy="14" r="18" fill="#fff" opacity=".12"/>' +
    '<text x="32" y="42" text-anchor="middle" font-family="iranyekan,Vazirmatn,Arial,sans-serif" font-size="28" font-weight="800" fill="#fff">' +
    ch +
    '</text>' +
    '<rect x="20" y="49" width="24" height="3" rx="1.5" fill="#fff" opacity=".7"/></svg>'
  );
}

const AWN = ['#EF4056', '#2563EB', '#059669', '#D97706', '#7C3AED', '#0891B2', '#DB2777', '#4B5563'];

export function getStoreArt(sid: string, kind: string = 'digital'): string {
  let h = 0;
  String(sid).split('').forEach((ch) => {
    h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  });
  const c = AWN[h % AWN.length];
  let stripes = '';
  for (let i = 0; i < 6; i++) {
    stripes += '<path d="M' + (14 + i * 12) + ' 30h6v8a6 6 0 0 1-12 0z" fill="' + (i % 2 ? '#fff' : c) + '" opacity="' + (i % 2 ? '.9' : '1') + '"/>';
  }
  const goods =
    kind === 'food'
      ? '<circle cx="36" cy="62" r="5" fill="#F59E0B"/><circle cx="46" cy="64" r="4" fill="#EF4444"/><rect x="54" y="56" width="8" height="12" rx="2" fill="#10B981"/>'
      : '<rect x="30" y="54" width="14" height="10" rx="2" fill="#1F2937"/><rect x="31.5" y="55.5" width="11" height="7" rx="1" fill="#60A5FA"/><rect x="50" y="52" width="7" height="13" rx="2" fill="#1F2937"/><circle cx="62" cy="61" r="4" fill="none" stroke="#1F2937" stroke-width="2"/>';

  return svg(
    '<rect x="14" y="26" width="68" height="56" rx="6" fill="#F8F5EE" stroke="currentColor" stroke-width="2"/>' +
    '<rect x="18" y="16" width="60" height="12" rx="4" fill="' +
    c +
    '"/>' +
    stripes +
    '<rect x="24" y="46" width="48" height="26" rx="3" fill="#E7EEF6" stroke="currentColor" stroke-width="1.6"/>' +
    goods +
    '<rect x="66" y="58" width="10" height="24" rx="2" fill="' +
    c +
    '" opacity=".85"/>'
  );
}
