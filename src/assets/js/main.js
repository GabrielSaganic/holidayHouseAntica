/* Holiday House Antica – page behaviour (no dependencies). */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Contact details: decoded here so they never sit in the HTML as plain text ---------- */
  // Mirror of obfuscate() in build.py: base64 → UTF-8 → reverse.
  function reveal(encoded) {
    var bytes = Uint8Array.from(atob(encoded), function (ch) { return ch.charCodeAt(0); });
    return Array.from(new TextDecoder().decode(bytes)).reverse().join('');
  }
  document.querySelectorAll('[data-obf-href]').forEach(function (el) {
    el.href = reveal(el.getAttribute('data-obf-href'));
  });
  document.querySelectorAll('[data-obf-text]').forEach(function (el) {
    el.textContent = reveal(el.getAttribute('data-obf-text'));
  });

  /* ---------- Header: solid background after scrolling ---------- */
  var header = document.querySelector('[data-header]');
  function updateHeader() {
    header.classList.toggle('is-scrolled', window.scrollY > 40);
  }
  updateHeader();
  window.addEventListener('scroll', updateHeader, { passive: true });

  /* ---------- Mobile navigation ---------- */
  var navToggle = document.querySelector('[data-nav-toggle]');
  var nav = document.querySelector('[data-nav]');

  function setNav(open) {
    navToggle.setAttribute('aria-expanded', String(open));
    header.classList.toggle('nav-open', open);
    document.body.classList.toggle('no-scroll', open);
  }
  navToggle.addEventListener('click', function () {
    setNav(navToggle.getAttribute('aria-expanded') !== 'true');
  });
  nav.addEventListener('click', function (e) {
    if (e.target.closest('a')) setNav(false);
  });

  /* ---------- Remember the chosen language (used by the root redirect) ---------- */
  document.querySelectorAll('[data-lang]').forEach(function (link) {
    link.addEventListener('click', function () {
      try { localStorage.setItem('lang', link.getAttribute('data-lang')); } catch (e) { /* storage blocked */ }
    });
  });

  /* ---------- Room tabs ---------- */
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.room-tab'));

  function selectTab(tab, moveFocus) {
    tabs.forEach(function (t) {
      var active = t === tab;
      t.setAttribute('aria-selected', String(active));
      t.tabIndex = active ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')).classList.toggle('is-active', active);
    });
    if (moveFocus) tab.focus();
  }

  tabs.forEach(function (tab, i) {
    tab.addEventListener('click', function () { selectTab(tab, false); });
    tab.addEventListener('keydown', function (e) {
      var next = null;
      if (e.key === 'ArrowRight') next = tabs[(i + 1) % tabs.length];
      else if (e.key === 'ArrowLeft') next = tabs[(i - 1 + tabs.length) % tabs.length];
      else if (e.key === 'Home') next = tabs[0];
      else if (e.key === 'End') next = tabs[tabs.length - 1];
      if (next) { e.preventDefault(); selectTab(next, true); }
    });
  });

  /* ---------- Lightbox ---------- */
  var lightbox = document.querySelector('[data-lightbox]');
  var lbImg = lightbox.querySelector('[data-lb-img]');
  var lbCaption = lightbox.querySelector('[data-lb-caption]');
  var items = [];
  var index = 0;
  var lastFocus = null;

  function show(i) {
    index = (i + items.length) % items.length;
    var item = items[index];
    lbImg.src = item.getAttribute('href');
    lbImg.alt = item.querySelector('img').alt;
    lbCaption.textContent = item.getAttribute('data-caption') + ' · ' + (index + 1) + ' / ' + items.length;
    // Preload neighbours for instant navigation.
    [index + 1, index - 1].forEach(function (n) {
      var neighbour = items[(n + items.length) % items.length];
      if (neighbour) (new Image()).src = neighbour.getAttribute('href');
    });
  }

  function openLightbox(item) {
    items = Array.prototype.slice.call(item.closest('.gallery').querySelectorAll('.gallery-item'));
    lastFocus = document.activeElement;
    show(items.indexOf(item));
    lightbox.hidden = false;
    document.body.classList.add('no-scroll');
    lightbox.querySelector('[data-lb-close]').focus();
  }

  function closeLightbox() {
    lightbox.hidden = true;
    lbImg.removeAttribute('src');
    document.body.classList.remove('no-scroll');
    if (lastFocus) lastFocus.focus();
  }

  document.addEventListener('click', function (e) {
    var item = e.target.closest('.gallery-item');
    if (!item) return;
    e.preventDefault();
    openLightbox(item);
  });

  lightbox.querySelector('[data-lb-close]').addEventListener('click', closeLightbox);
  lightbox.querySelector('[data-lb-prev]').addEventListener('click', function () { show(index - 1); });
  lightbox.querySelector('[data-lb-next]').addEventListener('click', function () { show(index + 1); });
  lightbox.addEventListener('click', function (e) {
    if (e.target === lightbox) closeLightbox();
  });

  document.addEventListener('keydown', function (e) {
    if (lightbox.hidden) return;
    if (e.key === 'Escape') closeLightbox();
    else if (e.key === 'ArrowRight') show(index + 1);
    else if (e.key === 'ArrowLeft') show(index - 1);
    else if (e.key === 'Tab') {
      // Keep keyboard focus inside the dialog.
      var focusable = lightbox.querySelectorAll('button');
      var first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  // Swipe left/right on touch screens.
  var touchX = null;
  lightbox.addEventListener('touchstart', function (e) { touchX = e.changedTouches[0].clientX; }, { passive: true });
  lightbox.addEventListener('touchend', function (e) {
    if (touchX === null) return;
    var dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 45) show(index + (dx < 0 ? 1 : -1));
    touchX = null;
  });

  /* ---------- Reveal sections on scroll ---------- */
  var revealEls = document.querySelectorAll('.reveal');
  if (reduceMotion || !('IntersectionObserver' in window)) {
    revealEls.forEach(function (el) { el.classList.add('is-visible'); });
  } else {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    revealEls.forEach(function (el) { observer.observe(el); });
  }

  /* ---------- Inquiry form: opens the visitor's mail app with a pre-filled message ---------- */
  var form = document.querySelector('[data-inquiry]');
  var arrival = form.querySelector('[data-arrival]');
  var departure = form.querySelector('[data-departure]');
  var today = new Date();
  today.setMinutes(today.getMinutes() - today.getTimezoneOffset());
  arrival.min = today.toISOString().slice(0, 10);
  departure.min = arrival.min;
  arrival.addEventListener('change', function () {
    departure.min = arrival.value || arrival.min;
    if (departure.value && departure.value < departure.min) departure.value = '';
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!form.reportValidity()) return;

    var lines = [];
    form.querySelectorAll('.field').forEach(function (field) {
      var input = field.querySelector('input, select, textarea');
      var label = field.querySelector('span').textContent;
      if (input && input.value.trim()) {
        lines.push(input.tagName === 'TEXTAREA' ? '\n' + input.value.trim() : label + ': ' + input.value.trim());
      }
    });

    var href = 'mailto:' + reveal(form.getAttribute('data-obf-email')) +
      '?subject=' + encodeURIComponent(form.getAttribute('data-subject')) +
      '&body=' + encodeURIComponent(lines.join('\n'));
    window.location.href = href;
  });
})();
