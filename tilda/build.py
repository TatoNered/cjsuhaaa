import re, sys
src = open('/home/claude/cjsuhaaa/index.html', encoding='utf-8').read()
ROOT = '#ironfolk'

head  = src.split('</head>')[0]
fonts = re.findall(r'<link[^>]*fonts\.(?:googleapis|gstatic)[^>]*>', head)
css   = src.split('<style>')[1].split('</style>')[0]
body  = src.split('<body class="is-loading">')[1].split('<script>')[0]
js    = src.split('<script>')[1].split('</script>')[0]

# ---------- CSS: префиксуем каждый селектор ----------
def prefix_selector(sel):
    out = []
    for part in sel.split(','):
        p = part.strip()
        if not p: continue
        if p in (':root', 'html'):
            out.append(ROOT)
        elif p == 'body':
            out.append(ROOT)
        elif p.startswith('body'):                      # body.is-loading .panel img
            out.append(ROOT + p[4:])
        elif p.startswith('html'):
            out.append(ROOT + p[4:])
        elif p.startswith('::'):                        # ::selection
            out.append(f'{ROOT} {p}')
        elif p.startswith('*'):                         # *, *::before
            out.append(f'{ROOT} {p}')
        elif p.startswith(ROOT):
            out.append(p)
        else:
            out.append(f'{ROOT} {p}')
    return ', '.join(out)

def walk(text):
    res, i, n = [], 0, len(text)
    while i < n:
        br = text.find('{', i)
        if br == -1:
            res.append(text[i:]); break
        sel = text[i:br]
        # найти парную закрывающую
        depth, j = 1, br + 1
        while j < n and depth:
            if text[j] == '{': depth += 1
            elif text[j] == '}': depth -= 1
            j += 1
        inner = text[br+1:j-1]
        s = sel.strip()
        if s.startswith('@media') or s.startswith('@supports'):
            res.append(sel + '{' + walk(inner) + '}')
        elif s.startswith('@keyframes') or s.startswith('@font-face'):
            res.append(sel + '{' + inner + '}')          # внутри не трогаем
        else:
            lead = sel[:len(sel)-len(sel.lstrip())]
            res.append(lead + prefix_selector(s) + '{' + inner + '}')
        i = j
    return ''.join(res)

# комментарии сохраняем отдельно, чтобы не ломали парсер
comments = []
def stash(m):
    comments.append(m.group(0)); return f'/*__C{len(comments)-1}__*/'
css_nc = re.sub(r'/\*.*?\*/', stash, css, flags=re.S)
css_nc = re.sub(r'/\*__C\d+__\*/', '', css_nc)           # убираем из потока
out_css = walk(css_nc)

# правило html{} с scroll-padding — вернём глобально, оно безвредно и нужно якорям
out_css = (f"html{{scroll-padding-top:86px}}\n"
           f"{ROOT}{{position:relative;--tmenu:0px}}\n"
           + out_css
           + f"\n/* сдвиг под меню Тильды: поставьте --tmenu:60px в блоке {ROOT} выше */\n"
           + f"{ROOT} .nav{{top:var(--tmenu)}}\n"
           + f"@media (min-width:901px){{{ROOT} .order__stage{{top:calc(90px + var(--tmenu))}}}}\n"
           + f"{ROOT} section[id]{{scroll-margin-top:calc(72px + var(--tmenu))}}\n"
           + f"{ROOT} .order .step[id]{{scroll-margin-top:calc(96px + var(--tmenu))}}\n"
           # body{overflow-x:hidden} после префиксации превращает контейнер
           # в скролл-контейнер и ломает каждый position:sticky внутри.
           # clip обрезает по горизонтали, но скролл-контейнер не создаёт.
           + f"\n/* не менять: hidden здесь ломает sticky (фото в коллекции и конфигураторе) */\n"
           + f"{ROOT},{ROOT}.is-loading{{overflow-x:clip!important;overflow-y:visible!important}}\n")

# ---------- JS: body -> контейнер ----------
js = js.replace("document.body.classList", "ROOT.classList")
js = js.replace("  const $  = (s, r=document) => r.querySelector(s);",
                "  const ROOT = document.getElementById('ironfolk');\n  const $  = (s, r=ROOT) => r.querySelector(s);")
js = js.replace("  const $$ = (s, r=document) => [...r.querySelectorAll(s)];",
                "  const $$ = (s, r=ROOT) => [...r.querySelectorAll(s)];")
# блокировка скролла страницы на время прелоадера
js = js.replace("const finishLoad = () => {",
                "const finishLoad = () => {\n    document.documentElement.style.overflow = '';")
js = js.replace("  /* ---------- nav ---------- */",
                "  document.documentElement.style.overflow = 'hidden';\n\n  /* ---------- nav ---------- */")

# ================= Тильда: каталог, цены, корзина =================
CDN = {
  'gzhel':     'https://static.tildacdn.com/stor3531-3465-4538-a463-306239363465/a1392346638b0384306f5e7f5eaa6d87.jpg',
  'khokhloma': 'https://static.tildacdn.com/stor6466-3462-4338-a330-643239373234/26d06410bd45b6f4773bcfc5a8a27e86.jpg',
  'iron':      'https://static.tildacdn.com/stor3932-6665-4134-b565-383062343763/043e70bc0529953905b2a62c6c9404a3.jpg',
}
CAT_REC = '4831817501'          # блок ST340 с разделом CERAMICS Iron Folk (скрыт)
UIDS = {'gzhel':'574264069383','khokhloma':'744794325043','iron':'308465064463'}
SKUS = {'gzhel':'IF-GZHEL','khokhloma':'IF-ZHAR','iron':'IF-CHUGUN'}
PNAM = {'gzhel':'Керамическая пивная кружка Iron Folk «Синий дым»',
        'khokhloma':'Керамическая пивная кружка Iron Folk «Жар»',
        'iron':'Керамическая пивная кружка Iron Folk «Чугун»'}

# картинки -> Tilda CDN
for k, u in CDN.items():
    body = body.replace('img/%s.jpg' % k, u)
    js   = js.replace('img/%s.jpg' % k, u)

CART_SVG = ('<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6">'
            '<path d="M1.5 2.2h2l1.7 7.6h7.1L14 4.6H5.2"/>'
            '<circle cx="6.6" cy="13" r="1.1"/><circle cx="12" cy="13" r="1.1"/></svg>')

def buyrow(k):
    return ('\n        <div class="buyrow">'
            '<span class="buyrow__price" data-price-for="%s"></span>'
            '<button class="btn magnetic btn--buy" type="button" data-cart="%s" data-cursor>'
            'В корзину %s</button></div>' % (k, k, CART_SVG))

for k in UIDS:
    body = re.sub(r'(<button class="btn magnetic" data-pick="%s".*?</button>)' % k,
                  lambda m, k=k: buyrow(k) + '\n        ' + m.group(1),
                  body, count=1, flags=re.S)

body = body.replace(
    '<p>Перезвоним, уточним детали и сроки. Оплата — после подтверждения.</p>',
    '<button class="btn btn--ghost magnetic" type="button" id="buyNow" data-cursor>'
    'Купить сейчас ' + CART_SVG + '</button>'
    '<p>Перезвоним, уточним детали и сроки. Оплата — после подтверждения.</p>')

out_css += (
  "\n/* каталог Тильды: нужен для цен и корзины, визуально скрыт */\n"
  "#rec%s{position:relative!important;height:1px!important;min-height:0!important;"
  "max-height:1px!important;overflow:hidden!important;opacity:.01!important;"
  "pointer-events:none!important;padding:0!important;margin:0!important;border:0!important}\n"
  "#record%s{height:1px!important;min-height:0!important;max-height:1px!important;"
  "overflow:hidden!important}\n"
  "%s .buyrow{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-top:34px;align-self:flex-start}\n"
  "%s .buyrow .btn{margin-top:0;align-self:auto}\n"
  "%s .buyrow__price{font:700 clamp(20px,3.6vw,26px)/1 var(--f-serif);color:var(--c,var(--ink))}\n"
  "%s .buyrow .btn[hidden]{display:none}\n"
  "%s .btn--buy{--b:var(--c)}\n"
  "%s .chapter .buyrow + .btn[data-pick]{margin-top:16px;background:transparent;"
  "color:var(--ink);border:1px solid var(--line)}\n"
  "%s .chapter .buyrow + .btn[data-pick]:hover{border-color:var(--c);box-shadow:none}\n"
  "@media (max-width:620px){%s .buyrow{gap:12px;margin-top:26px}"
  "%s .buyrow .btn{flex:1 1 auto;justify-content:center}}\n"
  % (CAT_REC, CAT_REC, ROOT, ROOT, ROOT, ROOT, ROOT, ROOT, ROOT, ROOT, ROOT))

# PRICES -> живые цены из каталога
js = re.sub(r'const PRICES = \{[\s\S]*?\n  \};',
            'const PRICES = new Proxy({}, { get: (t, k) => tCatalogPrice(String(k)) });',
            js, count=1)

bridge = """

  /* ============ Тильда: цены из каталога и корзина ============ */
  function tCatCard(key) {
    var uid = %s[key];
    if (!uid) return null;
    return document.querySelector('#rec%s .js-product[data-product-uid="' + uid + '"]');
  }
  function tCatalogPrice(key) {
    var c = tCatCard(key); if (!c) return null;
    var el = c.querySelector('.js-product-price, .js-store-prod-price-val');
    if (!el) return null;
    var n = parseInt(String(el.textContent).replace(/[^0-9]/g, ''), 10);
    return (isFinite(n) && n > 0) ? n : null;
  }
  // собрать товар для корзины прямо из карточки каталога —
  // работает и для кружек, и для упаковки
  function tAddCardToCart(card, qty) {
    if (!card || typeof window.tcart__addProduct !== 'function') return;
    var q = function (sel) { var e = card.querySelector(sel); return e ? e.textContent.trim() : ''; };
    var price = parseInt(q('.js-product-price, .js-store-prod-price-val').replace(/[^0-9]/g, ''), 10);
    if (!isFinite(price) || price <= 0) return;
    var d = card.dataset;
    window.tcart__addProduct({
      name: q('.js-product-name'), price: price, sku: q('.js-product-sku'),
      img: d.productImg || '', url: d.productUrl || location.href,
      quantity: Math.max(1, (qty | 0) || 1),
      uid: d.productUid, lid: d.productLid || d.productUid, gen_uid: d.productGenUid,
      part_uids: d.productPartUid ? [d.productPartUid] : [],
      recid: '%s',
      pack_label: d.productPackLabel, pack_x: d.productPackX,
      pack_y: d.productPackY, pack_z: d.productPackZ, pack_m: d.productPackM
    });
  }
  function tAddToCart(key, qty) {
    var card = tCatCard(key), price = tCatalogPrice(key);
    if (!card || !price || typeof window.tcart__addProduct !== 'function') {
      // каталог недоступен — не теряем клиента, ведём в форму предзаказа
      setPick(key, Math.max(1, (qty | 0) || 1));
      goToOrder();
      return;
    }
    var d = card.dataset;
    window.tcart__addProduct({
      name: %s[key], price: price, sku: %s[key],
      img: d.productImg || '', url: d.productUrl || location.href,
      quantity: Math.max(1, (qty | 0) || 1),
      uid: d.productUid, lid: d.productLid || d.productUid, gen_uid: d.productGenUid,
      part_uids: d.productPartUid ? [d.productPartUid] : [],
      recid: '%s',
      pack_label: d.productPackLabel, pack_x: d.productPackX,
      pack_y: d.productPackY, pack_z: d.productPackZ, pack_m: d.productPackM
    });
  }
  function tSyncPrices() {
    var ready = false;
    $$('[data-price-for]').forEach(function (el) {
      var p = tCatalogPrice(el.dataset.priceFor);
      el.textContent = p ? rub(p) : 'цена по запросу';
      var b = el.parentElement.querySelector('[data-cart]');
      if (b) b.hidden = !p || !SALE_ON;
      if (p) ready = true;
    });
    $$('.opt[data-mug]').forEach(function (b) {
      var p = tCatalogPrice(b.dataset.mug), el = b.querySelector('.opt__price');
      if (el) el.textContent = p ? rub(p) : 'по запросу';
    });
    render();
    return ready;
  }
  $$('[data-cart]').forEach(function (b) {
    b.addEventListener('click', function () { tAddToCart(b.dataset.cart, 1); });
  });
  var tBuyNow = $('#buyNow');
  if (tBuyNow && !SALE_ON) tBuyNow.hidden = true;
  if (tBuyNow) tBuyNow.addEventListener('click', function () {
    // в корзину уходят все выбранные кружки, каждая со своим количеством
    var any = false;
    Object.keys(state.picks).forEach(function (k) {
      if (state.picks[k] > 0) { tAddToCart(k, state.picks[k]); any = true; }
    });
    // и выбранная упаковка — отдельными позициями, со своей ценой
    Object.keys(state.boxes).forEach(function (k) {
      if (state.boxes[k] > 0) tAddCardToCart(boxCard(k), state.boxes[k]);
    });
    if (!any) {
      $('#optMug').classList.add('err');
      $('#optMug').scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' });
    }
  });
  if (!tSyncPrices()) {
    var tTries = 0;
    var tTimer = setInterval(function () {
      if (tSyncPrices() || ++tTries > 60) clearInterval(tTimer);
    }, 250);
  }
""" % ('%s' % repr(UIDS).replace("'", '"'), CAT_REC, CAT_REC,
       repr(PNAM).replace("'", '"'), repr(SKUS).replace("'", '"'), CAT_REC)

_i = js.rindex('})();')
js = js[:_i] + bridge + '\n' + js[_i:]

block = ('<!-- Iron Folk — блок для Тильды (T123 «HTML-код»). Вставлять целиком. -->\n'
         + '\n'.join(fonts) + '\n\n<style>\n' + out_css.strip() + '\n</style>\n\n'
         + f'<div id="ironfolk" class="is-loading">\n' + body.strip() + '\n</div>\n\n'
         + '<script>\n(() => {\n' + js.split('(() => {',1)[1].rsplit('})();',1)[0] + '})();\n</script>\n')

open('ironfolk-tilda.html','w',encoding='utf-8').write(block)
print('готово, размер блока:', len(block))
print('селекторов с префиксом:', out_css.count(ROOT))
print('медиазапросов:', out_css.count('@media'))
