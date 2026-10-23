/* تصویرهای برداری محصولات (جایگزین عکس تا وقتی عکس واقعی ندارید)
   NQ.art(kind, رنگ بدنه) ← رشتهٔ SVG. رنگ خطوط از currentColor می‌آید و با حالت تاریک عوض می‌شود. */
(function (NQ) {
  'use strict';
  var L = 'stroke="currentColor" stroke-width="2.4"';
  function svg(inner) {
    return '<svg viewBox="0 0 96 96" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
      '<ellipse cx="48" cy="87" rx="24" ry="3.4" fill="currentColor" opacity=".08"/>' + inner + '</svg>';
  }
  function keys(cols, rows, x0, y0, px, py, w, h) {
    var s = '';
    for (var r = 0; r < rows; r++) for (var c = 0; c < cols; c++)
      s += '<rect x="' + (x0 + c * px) + '" y="' + (y0 + r * py) + '" width="' + w + '" height="' + h + '" rx="1.2" fill="currentColor" opacity=".22"/>';
    return s;
  }
  var A = {
    over: function (c) {
      var band = 'M24 58V46a24 24 0 0 1 48 0v12';
      return '<path d="' + band + '" stroke="currentColor" stroke-width="9"/><path d="' + band + '" stroke="' + c + '" stroke-width="5"/>' +
        '<rect x="13" y="50" width="20" height="32" rx="10" fill="' + c + '" ' + L + '/><rect x="63" y="50" width="20" height="32" rx="10" fill="' + c + '" ' + L + '/>' +
        '<rect x="17" y="59" width="6" height="14" rx="3" fill="currentColor" opacity=".22"/><rect x="73" y="59" width="6" height="14" rx="3" fill="currentColor" opacity=".22"/>';
    },
    buds: function (c) {
      return '<rect x="40" y="32" width="7" height="24" rx="3.5" fill="' + c + '" ' + L + '/><rect x="49" y="32" width="7" height="24" rx="3.5" fill="' + c + '" ' + L + '/>' +
        '<circle cx="36" cy="30" r="10" fill="' + c + '" ' + L + '/><circle cx="60" cy="30" r="10" fill="' + c + '" ' + L + '/>' +
        '<rect x="20" y="54" width="56" height="30" rx="15" fill="' + c + '" ' + L + '/><path d="M22 66h52" stroke="currentColor" stroke-width="1.8" opacity=".35"/>' +
        '<circle cx="48" cy="75" r="2.2" fill="currentColor" opacity=".55"/>';
    },
    kb75: function (c) {
      return '<rect x="8" y="28" width="80" height="42" rx="7" fill="' + c + '" ' + L + '/>' + keys(11, 3, 13, 33, 6.6, 7.2, 5, 4.8) +
        keys(3, 1, 13, 54.6, 6.6, 7.2, 5, 4.8) + '<rect x="32.8" y="54.6" width="31.4" height="4.8" rx="1.2" fill="currentColor" opacity=".22"/>' + keys(3, 1, 65.8, 54.6, 6.6, 7.2, 5, 4.8);
    },
    tkl: function (c) {
      return '<rect x="6" y="24" width="84" height="48" rx="7" fill="' + c + '" ' + L + '/>' + keys(13, 4, 11, 29, 5.9, 6.6, 4.3, 4.4) +
        keys(3, 1, 11, 55.4, 5.9, 6.6, 4.3, 4.4) + '<rect x="30" y="55.4" width="29" height="4.4" rx="1.2" fill="currentColor" opacity=".22"/>' + keys(4, 1, 64.1, 55.4, 5.9, 6.6, 4.3, 4.4);
    },
    gan: function (c) {
      return '<rect x="38" y="14" width="5" height="16" rx="1.6" fill="currentColor" opacity=".8"/><rect x="53" y="14" width="5" height="16" rx="1.6" fill="currentColor" opacity=".8"/>' +
        '<rect x="24" y="28" width="48" height="54" rx="12" fill="' + c + '" ' + L + '/><path d="M38 42h20" stroke="currentColor" stroke-width="3" opacity=".25"/>' +
        '<rect x="40" y="58" width="16" height="8" rx="4" fill="currentColor" opacity=".7"/><circle cx="62" cy="38" r="2" fill="currentColor" opacity=".5"/>';
    },
    dual: function (c) {
      return '<rect x="37" y="14" width="5" height="16" rx="1.6" fill="currentColor" opacity=".8"/><rect x="54" y="14" width="5" height="16" rx="1.6" fill="currentColor" opacity=".8"/>' +
        '<rect x="20" y="28" width="56" height="54" rx="12" fill="' + c + '" ' + L + '/><path d="M34 42h28" stroke="currentColor" stroke-width="3" opacity=".25"/>' +
        '<rect x="32" y="58" width="14" height="8" rx="4" fill="currentColor" opacity=".7"/><rect x="50" y="58" width="14" height="8" rx="2" fill="currentColor" opacity=".7"/>';
    },
    bank: function (c) {
      return '<rect x="29" y="10" width="38" height="76" rx="11" fill="' + c + '" ' + L + '/>' +
        [22, 29, 36, 43].map(function (y) { return '<rect x="39" y="' + y + '" width="18" height="3.6" rx="1.8" fill="currentColor" opacity=".45"/>'; }).join('') +
        '<rect x="41" y="73" width="14" height="5" rx="2.5" fill="currentColor" opacity=".6"/>';
    },
    nano: function (c) {
      return '<rect x="31" y="16" width="34" height="66" rx="9" fill="' + c + '" ' + L + '/><rect x="38" y="25" width="20" height="11" rx="3" fill="currentColor" opacity=".25"/>' +
        '<path d="M42 30h12" stroke="currentColor" stroke-width="2" opacity=".6"/><rect x="42" y="70" width="12" height="5" rx="2.5" fill="currentColor" opacity=".6"/>';
    },
    raze: function (c) {
      return '<path d="M48 12c-15 0-23 11-23 27v22c0 15 10 25 23 25s23-10 23-25V39c0-16-8-27-23-27z" fill="' + c + '" ' + L + '/>' +
        '<path d="M25 42h46M48 12v30" stroke="currentColor" stroke-width="2" opacity=".45"/><rect x="44.5" y="22" width="7" height="12" rx="3.5" fill="currentColor" opacity=".75"/>';
    },
    glide: function (c) {
      return '<path d="M48 14c-13 0-20 9-20 24l-3 26c-1 12 8 22 23 22s24-10 23-22l-3-26c0-15-7-24-20-24z" fill="' + c + '" ' + L + '/>' +
        '<path d="M28 41c6 3 14 4 20 4s14-1 20-4M48 14v31" stroke="currentColor" stroke-width="2" opacity=".45"/><rect x="44.5" y="23" width="7" height="12" rx="3.5" fill="currentColor" opacity=".75"/>' +
        '<rect x="21" y="50" width="6" height="12" rx="3" fill="currentColor" opacity=".6"/><circle cx="48" cy="68" r="2.2" fill="currentColor" opacity=".5"/>';
    }
  };
  NQ.art = function (kind, color) { return svg((A[kind] || A.raze)(color || '#8C9692')); };
})(window.NQ = window.NQ || {});
