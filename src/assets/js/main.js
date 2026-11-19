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
  var navToggle = document.querySelector('[data-nav-toggle]');
  var nav = document.querySelector('[data-nav]');

  if (header) {
    var updateHeader = function () {
      header.classList.toggle('is-scrolled', window.scrollY > 40);
    };
    updateHeader();
    window.addEventListener('scroll', updateHeader, { passive: true });
  }

  /* ---------- Mobile navigation ---------- */
  function setNav(open) {
    navToggle.setAttribute('aria-expanded', String(open));
    header.classList.toggle('nav-open', open);
    document.body.classList.toggle('no-scroll', open);
  }
  if (header && navToggle && nav) {
    navToggle.addEventListener('click', function () {
      setNav(navToggle.getAttribute('aria-expanded') !== 'true');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) setNav(false);
    });
  }

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
  if (lightbox) (function () {
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
  })();

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
  if (form) (function () {
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

    var email = reveal(form.getAttribute('data-obf-email'));
    var subject = form.getAttribute('data-subject');
    var body = lines.join('\n');
    showAlternatives(email, subject, body);
    window.location.href = 'mailto:' + email + '?subject=' + encodeURIComponent(subject) +
      '&body=' + encodeURIComponent(body);
  });

  // Many visitors use webmail and have no e-mail app, so mailto: silently does nothing.
  // Offer the same pre-filled message via WhatsApp, Gmail or the clipboard.
  var alt = form.querySelector('[data-inquiry-alt]');
  var copyText = '';
  function showAlternatives(email, subject, body) {
    var wa = form.getAttribute('data-obf-wa');
    var waLink = alt.querySelector('[data-alt-whatsapp]');
    var number = wa ? reveal(wa) : '';
    waLink.hidden = !number;
    if (number) waLink.href = 'https://wa.me/' + number + '?text=' + encodeURIComponent(subject + '\n\n' + body);
    alt.querySelector('[data-alt-gmail]').href = 'https://mail.google.com/mail/?view=cm&fs=1&to=' +
      encodeURIComponent(email) + '&su=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
    copyText = form.getAttribute('data-to') + ': ' + email + '\n' + subject + '\n\n' + body;
    alt.hidden = false;
  }
  var copyBtn = alt.querySelector('[data-alt-copy]');
  copyBtn.addEventListener('click', function () {
    var label = copyBtn.querySelector('span');
    var original = label.textContent;
    function done() {
      label.textContent = copyBtn.getAttribute('data-copied');
      setTimeout(function () { label.textContent = original; }, 2000);
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(copyText).then(done);
    } else {
      // Fallback for older browsers / non-HTTPS previews.
      var ta = document.createElement('textarea');
      ta.value = copyText; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(); } catch (e) { /* ignore */ }
      ta.remove();
    }
  });
  })();

  /* ---------- Availability calendar ---------- */
  var cal = document.querySelector('[data-calendar]');
  if (cal) (function () {
    var data = JSON.parse(cal.querySelector('[data-cal-data]').textContent);
    var tr = data.t;
    var monthsEl = cal.querySelector('[data-cal-months]');
    var messageEl = cal.querySelector('[data-cal-message]');
    var actionsEl = cal.querySelector('[data-cal-actions]');
    var MAX_OFFSET = 18;
    var offset = 0;
    var start = null;
    var end = null;

    // All dates are handled as 'YYYY-MM-DD' strings in UTC, so time zones never shift a day.
    function iso(d) { return d.toISOString().slice(0, 10); }
    function parse(s) { return new Date(s + 'T00:00:00Z'); }
    function addDays(s, n) { var d = parse(s); d.setUTCDate(d.getUTCDate() + n); return iso(d); }
    function nights(a, b) { return Math.round((parse(b) - parse(a)) / 864e5); }
    function fill(text, values) {
      return text.replace(/\{(\w+)\}/g, function (m, k) { return k in values ? values[k] : m; });
    }

    var now = new Date();
    var today = iso(new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())));
    var fmtMonth = new Intl.DateTimeFormat(data.lang, { month: 'long', year: 'numeric', timeZone: 'UTC' });
    var fmtDay = new Intl.DateTimeFormat(data.lang, { day: 'numeric', month: 'short', timeZone: 'UTC' });
    var fmtLong = new Intl.DateTimeFormat(data.lang, { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
    var fmtWeekday = new Intl.DateTimeFormat(data.lang, { weekday: 'short', timeZone: 'UTC' });

    // A night is booked when it falls inside [from, to) of any booking.
    function isBooked(day) {
      return data.booked.some(function (r) { return day >= r[0] && day < r[1]; });
    }
    function rangeFree(a, b) {
      for (var d = a; d < b; d = addDays(d, 1)) if (isBooked(d)) return false;
      return true;
    }
    // The season a night falls into (periods are 'MM-DD' pairs), or null.
    function season(day) {
      var mmdd = day.slice(5);
      for (var i = 0; i < data.seasons.length; i++) {
        var periods = data.seasons[i].periods;
        for (var j = 0; j < periods.length; j++) {
          if (mmdd >= periods[j][0] && mmdd <= periods[j][1]) return data.seasons[i];
        }
      }
      return null;
    }
    function minStay(day) { var s = season(day); return s ? s.min : 0; }
    function money(n) { return fill(data.price_pattern, { p: n }); }
    // Total for the nights [a, b), or null when some night has no price.
    function total(a, b) {
      var sum = 0;
      for (var d = a; d < b; d = addDays(d, 1)) {
        var s = season(d);
        if (!s) return null;
        sum += s.price;
      }
      return sum;
    }

    // Only nights that have a price can be booked. The departure day itself needs
    // no price (that night is not stayed), but every night before it does.
    function selectable(day) {
      if (day < today) return false;
      if (start && !end && day > start) return rangeFree(start, day) && total(start, day) !== null;
      return !isBooked(day) && season(day) !== null;
    }

    // Nightly price under the date (only for nights that can still be booked).
    function priceTag(day) {
      var s = day >= today && !isBooked(day) ? season(day) : null;
      return '<span class="cal-price">' + (s ? money(s.price) : '') + '</span>';
    }

    function renderMonth(year, month) {
      var first = new Date(Date.UTC(year, month, 1));
      var days = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
      var lead = (first.getUTCDay() + 6) % 7; // Monday first
      var html = '<div class="cal-month"><p class="cal-title">' + fmtMonth.format(first) + '</p>';
      html += '<div class="cal-grid" role="grid">';
      for (var w = 0; w < 7; w++) {
        html += '<span class="cal-wd">' + fmtWeekday.format(new Date(Date.UTC(2024, 0, 1 + w))) + '</span>';
      }
      for (var b = 0; b < lead; b++) html += '<span></span>';
      for (var d = 1; d <= days; d++) {
        var day = iso(new Date(Date.UTC(year, month, d)));
        var cls = ['cal-day'];
        if (day < today) cls.push('is-past');
        else if (isBooked(day)) cls.push('is-booked');
        else if (!season(day)) cls.push('is-closed');
        if (day === today) cls.push('is-today');
        if (day === start) cls.push('is-start');
        if (day === end) cls.push('is-end');
        if (start && end && day > start && day < end) cls.push('is-range');
        var ok = selectable(day);
        html += '<button type="button" class="' + cls.join(' ') + '" data-day="' + day + '"' +
          (ok ? '' : ' disabled') + ' aria-label="' + fmtLong.format(parse(day)) + '"' +
          ((day === start || day === end) ? ' aria-pressed="true"' : '') + '>' +
          '<span class="cal-num">' + d + '</span>' + priceTag(day) + '</button>';
      }
      return html + '</div></div>';
    }

    // One month on phones, two side by side on larger screens.
    var narrow = window.matchMedia('(max-width: 520px)');
    function render() {
      var base = new Date(Date.UTC(now.getFullYear(), now.getMonth() + offset, 1));
      monthsEl.innerHTML = renderMonth(base.getUTCFullYear(), base.getUTCMonth()) +
        (narrow.matches ? '' : renderMonth(base.getUTCFullYear(), base.getUTCMonth() + 1));
      cal.querySelector('[data-cal-prev]').disabled = offset <= 0;
      cal.querySelector('[data-cal-next]').disabled = offset >= MAX_OFFSET;
    }

    function updateStatus() {
      if (start && end) {
        var n = nights(start, end);
        var text = fill(tr.selection, { from: fmtDay.format(parse(start)), to: fmtDay.format(parse(end)), n: n });
        var sum = total(start, end);
        if (sum !== null) text += ' · ' + fill(tr.total, { price: money(sum) });
        messageEl.textContent = text;
        var min = minStay(start);
        if (min && n < min) {
          var warn = document.createElement('span');
          warn.className = 'cal-warn';
          warn.textContent = fill(tr.min_stay, { n: min });
          messageEl.appendChild(warn);
        }
        actionsEl.hidden = false;
      } else {
        messageEl.textContent = start ? tr.pick_departure : tr.hint;
        actionsEl.hidden = true;
      }
    }

    // Copy the chosen dates into the inquiry form.
    function syncForm() {
      var a = document.querySelector('[data-arrival]');
      var d = document.querySelector('[data-departure]');
      if (!a || !d) return;
      a.value = start || '';
      d.value = end || '';
      d.min = start || a.min;
    }

    monthsEl.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-day]');
      if (!btn || btn.disabled) return;
      var day = btn.getAttribute('data-day');
      if (start && !end && day > start) end = day;
      else { start = day; end = null; }
      render();
      updateStatus();
      syncForm();
      var again = monthsEl.querySelector('[data-day="' + day + '"]');
      if (again) again.focus();
    });

    cal.querySelector('[data-cal-prev]').addEventListener('click', function () { offset = Math.max(0, offset - 1); render(); });
    cal.querySelector('[data-cal-next]').addEventListener('click', function () { offset = Math.min(MAX_OFFSET, offset + 1); render(); });
    cal.querySelector('[data-cal-clear]').addEventListener('click', function () {
      start = end = null;
      render(); updateStatus(); syncForm();
    });
    cal.querySelector('[data-cal-updated]').textContent = fill(tr.updated, { date: fmtLong.format(parse(data.updated)) });

    if (narrow.addEventListener) narrow.addEventListener('change', render);
    render();
    updateStatus();
  })();

  /* ---------- Floating quick-contact buttons ---------- */
  var fab = document.querySelector('[data-fab]');
  if (fab) (function () {
    var hideOver = [document.querySelector('#contact'), document.querySelector('.site-footer')].filter(Boolean);
    var covered = 0;
    function update() {
      fab.classList.toggle('is-visible', window.scrollY > window.innerHeight * 0.6 && covered === 0);
    }
    if ('IntersectionObserver' in window) {
      var seen = new Set();
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) seen.add(en.target); else seen.delete(en.target); });
        covered = seen.size;
        update();
      });
      hideOver.forEach(function (el) { io.observe(el); });
    }
    window.addEventListener('scroll', update, { passive: true });
    update();
  })();
})();
