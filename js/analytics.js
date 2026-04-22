/* ===== КРОНОВЪ · Общая аналитика (БЛОК 10 ТЗ v2) =====
   Один файл подключается на всех страницах сайта.
   Активация: подставьте два ID в window.KRONOV_ANALYTICS_CONFIG
   (см. ANALYTICS_SETUP.md в корне репозитория).
*/
(function(){
  'use strict';

  // ===== КОНФИГУРАЦИЯ — единственное место, куда надо вставить ID =====
  // Замените 'G-XXXXXXXXXX' на ваш реальный Measurement ID из GA4
  // Замените 0 на ваш номер счётчика Яндекс.Метрики
  window.KRONOV_ANALYTICS_CONFIG = window.KRONOV_ANALYTICS_CONFIG || {
    ga4: 'G-XXXXXXXXXX',     // ← ВСТАВИТЬ ПОСЛЕ СОЗДАНИЯ GA4 (analytics.google.com)
    ym:  0,                    // ← ВСТАВИТЬ ПОСЛЕ СОЗДАНИЯ Метрики (metrika.yandex.by)
    meta: null                 // ← опционально (pixel.facebook.com)
  };

  var CFG = window.KRONOV_ANALYTICS_CONFIG;
  var isGA4Active = CFG.ga4 && CFG.ga4 !== 'G-XXXXXXXXXX';
  var isYMActive  = CFG.ym && Number(CFG.ym) > 0;

  // Экспортируем ID наружу, чтобы form-хэндлеры могли вызывать ym(…, 'reachGoal', …)
  if (isYMActive) window.YM_COUNTER_ID = Number(CFG.ym);

  // ===== GA4 init =====
  if (isGA4Active) {
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + CFG.ga4;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function(){ dataLayer.push(arguments); };
    gtag('js', new Date());
    gtag('config', CFG.ga4, { send_page_view: true });
  } else {
    // Заглушка — лог в консоль разработчика, ничего не отправляется
    window.gtag = function(){
      if (window.console && console.debug) console.debug('[GA4 stub]', Array.prototype.slice.call(arguments));
    };
  }

  // ===== Яндекс.Метрика init =====
  if (isYMActive) {
    (function(m,e,t,r,i,k,a){
      m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
      m[i].l=1*new Date();
      for (var j=0;j<document.scripts.length;j++){ if(document.scripts[j].src===r){return;} }
      k=e.createElement(t); a=e.getElementsByTagName(t)[0]; k.async=1; k.src=r; a.parentNode.insertBefore(k,a);
    })(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js', 'ym');
    ym(CFG.ym, 'init', {
      clickmap: true,
      trackLinks: true,
      accurateTrackBounce: true,
      webvisor: true,
      trackHash: true
    });
  } else {
    window.ym = function(){
      if (window.console && console.debug) console.debug('[YM stub]', Array.prototype.slice.call(arguments));
    };
  }

  // ===== Meta Pixel (опционально) =====
  if (CFG.meta) {
    !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');
    fbq('init', CFG.meta); fbq('track', 'PageView');
  }

  // ===== Единый хелпер отправки события в оба счётчика =====
  window.kronovTrack = function(eventName, params){
    params = params || {};
    try { if (window.gtag) gtag('event', eventName, params); } catch(e){}
    try { if (window.ym && isYMActive) ym(CFG.ym, 'reachGoal', eventName, params); } catch(e){}
    try { if (window.fbq && CFG.meta) fbq('trackCustom', eventName, params); } catch(e){}
  };

  // ===== Автотрекинг скролла (ТЗ 10.1: 25% / 50% / 75% / 100%) =====
  (function(){
    var fired = {25:false, 50:false, 75:false, 100:false};
    var throttle = false;
    function onScroll(){
      if (throttle) return;
      throttle = true;
      setTimeout(function(){ throttle = false; }, 250);
      var doc = document.documentElement;
      var scrolled = (window.scrollY || doc.scrollTop) + window.innerHeight;
      var total = doc.scrollHeight;
      if (total <= window.innerHeight) return;
      var pct = Math.round(scrolled / total * 100);
      [25,50,75,100].forEach(function(k){
        if (!fired[k] && pct >= k) {
          fired[k] = true;
          kronovTrack('scroll_depth', { depth: k, page: location.pathname });
        }
      });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
  })();

  // ===== Автотрекинг загрузки PDF (ТЗ 10.1: pdf_download) =====
  document.addEventListener('click', function(e){
    var a = e.target && e.target.closest && e.target.closest('a[href$=".pdf"], a[href*=".pdf?"]');
    if (!a) return;
    var filename = a.getAttribute('href').split('/').pop().split('?')[0];
    kronovTrack('pdf_download', { file: filename });
  }, true);

  // ===== Авто CTA-клики по data-cta-location =====
  document.addEventListener('click', function(e){
    var el = e.target && e.target.closest && e.target.closest('[data-cta-location]');
    if (!el) return;
    kronovTrack('cta_click', {
      cta_location: el.getAttribute('data-cta-location'),
      cta_label: (el.textContent || '').trim().slice(0, 80)
    });
  }, true);

  // ===== Авто model_view по клику на карточку модели =====
  document.addEventListener('click', function(e){
    var card = e.target && e.target.closest && e.target.closest('[data-model-view]');
    if (!card) return;
    kronovTrack('model_view', {
      model: card.getAttribute('data-model-view'),
      source: card.getAttribute('data-model-source') || 'catalog'
    });
  }, true);

  // ===== Клики по tel: / wa.me / viber / t.me (ТЗ: PHONE_CLICK, WHATSAPP_CLICK) =====
  document.addEventListener('click', function(e){
    var a = e.target && e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href') || '';
    if (href.indexOf('tel:') === 0) {
      kronovTrack('phone_click', { number: href.replace('tel:', ''), page: location.pathname });
    } else if (href.indexOf('wa.me') > -1 || href.indexOf('whatsapp') > -1) {
      kronovTrack('whatsapp_click', { page: location.pathname });
    } else if (href.indexOf('viber:') === 0) {
      kronovTrack('viber_click', { page: location.pathname });
    } else if (href.indexOf('t.me/') > -1) {
      kronovTrack('telegram_click', { page: location.pathname });
    }
  }, true);

  // ===== 60 секунд на странице (ТЗ: TIME_ON_PAGE_60) =====
  setTimeout(function(){
    kronovTrack('time_on_page_60', { page: location.pathname });
  }, 60000);

  // ===== catalog_click — клик по любой карточке каталога =====
  document.addEventListener('click', function(e){
    var link = e.target && e.target.closest && e.target.closest('.catalog-link, .catalog-card');
    if (!link) return;
    var model = link.getAttribute('data-model-view') || '';
    kronovTrack('catalog_click', { model: model, page: location.pathname });
  }, true);

  // Видимость для отладки в dev-tools
  window.kronovAnalyticsStatus = function(){
    return {
      ga4: isGA4Active ? CFG.ga4 : 'not configured',
      ym: isYMActive ? CFG.ym : 'not configured',
      meta: CFG.meta || 'not configured'
    };
  };
})();
