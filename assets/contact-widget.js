/* KRONOV floating contact widget — injects sticky mobile bar + desktop multi-button
   into any page with a single <script src="/assets/contact-widget.js" defer></script>. */
(function () {
  if (window.__kronovContactWidgetLoaded) return;
  window.__kronovContactWidgetLoaded = true;

  var PHONE = '+375296888629';
  var PHONE_URL = 'tel:+375296888629';
  var WA_URL = 'https://wa.me/375296888629';
  var VIBER_URL = 'viber://chat?number=%2B375296888629';
  var TG_URL = 'https://t.me/+375296888629';

  var CSS = [
    '.kcw-bar{display:none;position:fixed;bottom:0;left:0;right:0;z-index:9998;background:#1a1512;border-top:1px solid rgba(212,184,150,.1);padding:10px 12px}',
    '.kcw-bar-inner{display:flex;gap:8px}',
    '.kcw-bar a{flex:1;padding:12px 6px;text-align:center;border-radius:8px;font:600 13px/1 Montserrat,system-ui,sans-serif;text-decoration:none;letter-spacing:.2px}',
    '.kcw-call{background:#7A2E38;color:#F2EBE0}',
    '.kcw-wa{background:#25D366;color:#fff}',
    '.kcw-vi{background:#7360F2;color:#fff}',
    '.kcw-tg{background:#0088CC;color:#fff}',
    '@media(max-width:767px){.kcw-bar{display:block}body{padding-bottom:72px}}',
    '@media(min-width:768px){.kcw-bar{display:none}}',
    '.kcw-fab{position:fixed;bottom:24px;right:24px;z-index:9999;font-family:Montserrat,system-ui,sans-serif}',
    '.kcw-fab-main{width:60px;height:60px;border-radius:50%;background:#7A2E38;color:#F2EBE0;display:flex;align-items:center;justify-content:center;border:none;cursor:pointer;box-shadow:0 10px 28px rgba(122,46,56,.45);transition:transform .22s,background .22s}',
    '.kcw-fab-main:hover{background:#8E3542;transform:scale(1.06)}',
    '.kcw-fab.open .kcw-fab-main{background:#1a1512;transform:rotate(45deg)}',
    '.kcw-opts{position:absolute;bottom:72px;right:0;display:flex;flex-direction:column;gap:10px;opacity:0;pointer-events:none;transform:translateY(14px);transition:opacity .25s,transform .25s}',
    '.kcw-fab.open .kcw-opts{opacity:1;pointer-events:all;transform:translateY(0)}',
    '.kcw-opt{display:flex;align-items:center;gap:12px;background:#1a1512;color:#F2EBE0;padding:10px 16px 10px 18px;border-radius:28px;white-space:nowrap;box-shadow:0 6px 16px rgba(0,0,0,.2);font:500 13px/1 Montserrat,system-ui,sans-serif;text-decoration:none;transition:transform .2s}',
    '.kcw-opt:hover{transform:translateX(-3px)}',
    '.kcw-ic{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;flex-shrink:0}',
    '.kcw-ic.phone{background:#7A2E38}',
    '.kcw-ic.wa{background:#25D366}',
    '.kcw-ic.vi{background:#7360F2}',
    '.kcw-ic.tg{background:#0088CC}',
    '.kcw-phone-pill{position:fixed;bottom:28px;left:24px;z-index:9997;padding:12px 20px;background:rgba(26,21,18,.92);color:#F2EBE0;border-radius:28px;font:600 14px/1 Montserrat,system-ui,sans-serif;letter-spacing:.3px;box-shadow:0 8px 22px rgba(0,0,0,.35);text-decoration:none;backdrop-filter:blur(10px);border:1px solid rgba(212,184,150,.18);transition:transform .22s,background .22s}',
    '.kcw-phone-pill:hover{background:#7A2E38;transform:translateY(-2px)}',
    '.kcw-phone-pill .kcw-phone-ic{display:inline-block;vertical-align:middle;margin-right:8px}',
    '@media(max-width:767px){.kcw-fab,.kcw-phone-pill{display:none}}'
  ].join('');

  var ICONS = {
    phone: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>',
    wa: '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>',
    vi: '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M11.4 0C9.473.028 5.333.344 3.02 2.467 1.302 4.187.696 6.7.633 9.817c-.063 3.11-.138 8.932 5.474 10.514v2.414s-.037.978.61 1.177c.777.24 1.234-.502 1.979-1.302.408-.44.973-1.087 1.398-1.584 3.842.323 6.795-.416 7.13-.525.775-.252 5.167-.816 5.882-6.647.737-6.013-.36-9.81-2.334-11.526l-.012-.005c-.596-.549-2.99-2.29-8.336-2.312 0 0-.396-.025-1.024-.022z"/></svg>',
    tg: '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221l-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.446 1.394c-.14.18-.357.295-.6.295l.213-3.054 5.56-5.022c.24-.213-.054-.334-.373-.121L8.48 13.617l-2.95-.924c-.64-.203-.658-.643.136-.953l11.514-4.44c.538-.196 1.006.128.832.922z"/></svg>',
    chat: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>'
  };

  function inject() {
    // Не дублировать если на странице уже есть свой виджет (index.html)
    if (document.querySelector('.sticky-bar, .multi-btn')) return;

    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    var bar = document.createElement('div');
    bar.className = 'kcw-bar';
    bar.innerHTML =
      '<div class="kcw-bar-inner">' +
        '<a href="' + PHONE_URL + '" class="kcw-call" aria-label="Позвонить">Звонок</a>' +
        '<a href="' + WA_URL + '" class="kcw-wa" target="_blank" rel="noopener" aria-label="WhatsApp">WhatsApp</a>' +
        '<a href="' + VIBER_URL + '" class="kcw-vi" aria-label="Viber">Viber</a>' +
        '<a href="' + TG_URL + '" class="kcw-tg" target="_blank" rel="noopener" aria-label="Telegram">Telegram</a>' +
      '</div>';

    var fab = document.createElement('div');
    fab.className = 'kcw-fab';
    fab.innerHTML =
      '<div class="kcw-opts">' +
        '<a href="' + PHONE_URL + '" class="kcw-opt"><span>Позвонить</span><span class="kcw-ic phone">' + ICONS.phone + '</span></a>' +
        '<a href="' + WA_URL + '" class="kcw-opt" target="_blank" rel="noopener"><span>WhatsApp</span><span class="kcw-ic wa">' + ICONS.wa + '</span></a>' +
        '<a href="' + VIBER_URL + '" class="kcw-opt"><span>Viber</span><span class="kcw-ic vi">' + ICONS.vi + '</span></a>' +
        '<a href="' + TG_URL + '" class="kcw-opt" target="_blank" rel="noopener"><span>Telegram</span><span class="kcw-ic tg">' + ICONS.tg + '</span></a>' +
      '</div>' +
      '<button class="kcw-fab-main" type="button" aria-label="Связаться с нами">' + ICONS.chat + '</button>';

    var pill = document.createElement('a');
    pill.className = 'kcw-phone-pill';
    pill.href = PHONE_URL;
    pill.setAttribute('aria-label', 'Позвонить Алёне');
    pill.innerHTML = '<span class="kcw-phone-ic">' + ICONS.phone + '</span>' + PHONE;

    document.body.appendChild(bar);
    document.body.appendChild(fab);
    document.body.appendChild(pill);

    var mainBtn = fab.querySelector('.kcw-fab-main');
    mainBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      fab.classList.toggle('open');
    });
    document.addEventListener('click', function (e) {
      if (fab.classList.contains('open') && !fab.contains(e.target)) {
        fab.classList.remove('open');
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
})();
