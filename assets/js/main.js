/* ============================================================
   ProAffy - main.js
   Handles: i18n, mobile nav, accordion, form validation
   ============================================================ */

/* ── i18n ────────────────────────────────────────────────── */
async function loadI18n(lang = 'en') {
  try {
    const res = await fetch(`lang/${lang}.json`);
    if (!res.ok) return;
    const strings = await res.json();
    applyStrings(strings);
  } catch (_) {
    // silently fail - hardcoded HTML text already shows EN content
  }
}

function applyStrings(strings) {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (strings[key] !== undefined) el.textContent = strings[key];
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.dataset.i18nPlaceholder;
    if (strings[key] !== undefined) el.placeholder = strings[key];
  });
}

/* ── Mobile Nav ──────────────────────────────────────────── */
function initMobileNav() {
  const hamburger = document.getElementById('hamburger');
  const mobileMenu = document.getElementById('mobileMenu');
  if (!hamburger || !mobileMenu) return;

  hamburger.addEventListener('click', () => {
    const isOpen = mobileMenu.classList.toggle('open');
    hamburger.setAttribute('aria-expanded', String(isOpen));
    document.body.style.overflow = isOpen ? 'hidden' : '';
  });

  mobileMenu.querySelectorAll('.nav__mobile-link').forEach(link => {
    link.addEventListener('click', () => {
      mobileMenu.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    });
  });
}

/* ── Accordion ───────────────────────────────────────────── */
function initAccordion() {
  document.querySelectorAll('.accordion-item__trigger').forEach(trigger => {
    const item = trigger.closest('.accordion-item');
    const body = item.querySelector('.accordion-item__body');
    const icon = trigger.querySelector('.accordion-item__icon');

    // Set initial state from aria-expanded attribute
    const startOpen = trigger.getAttribute('aria-expanded') === 'true';
    if (startOpen) {
      item.setAttribute('open', '');
      body.style.display = 'block';
      icon.textContent = '−';
    }

    trigger.addEventListener('click', () => {
      const isOpen = item.hasAttribute('open');
      if (isOpen) {
        item.removeAttribute('open');
        body.style.display = 'none';
        icon.textContent = '+';
        trigger.setAttribute('aria-expanded', 'false');
      } else {
        item.setAttribute('open', '');
        body.style.display = 'block';
        icon.textContent = '−';
        trigger.setAttribute('aria-expanded', 'true');
      }
    });
  });
}

/* ── Contact Form ────────────────────────────────────────── */
function initContactForm() {
  const form = document.getElementById('contactForm');
  if (!form) return;

  const statusEl = document.getElementById('formStatus');

  form.addEventListener('submit', async e => {
    e.preventDefault();

    const firstName = form.firstName.value.trim();
    const lastName  = form.lastName.value.trim();
    const email     = form.email.value.trim();

    if (!firstName || !lastName) {
      showStatus('Please enter your first and last name.', 'error');
      return;
    }
    if (!isValidEmail(email)) {
      showStatus('Please enter a valid email address.', 'error');
      return;
    }

    const submitBtn = form.querySelector('[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending…';

    // Simulate async submission (replace with real endpoint later)
    await new Promise(r => setTimeout(r, 1000));

    showStatus('Thank you! We\'ll be in touch within one business day.', 'success');
    form.reset();
    submitBtn.disabled = false;
    submitBtn.textContent = 'Get My Free Pilot';
  });

  function showStatus(msg, type) {
    statusEl.textContent = msg;
    statusEl.style.display = 'block';
    statusEl.style.color = type === 'success' ? '#3B82F6' : '#ef4444';
  }
}

/* ── CTA Email Form ──────────────────────────────────────── */
function initCtaEmailForm() {
  const form = document.getElementById('ctaEmailForm');
  if (!form) return;

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const emailInput = form.querySelector('input[type="email"]');
    if (!isValidEmail(emailInput.value.trim())) {
      emailInput.style.borderColor = '#ff5555';
      return;
    }
    emailInput.style.borderColor = '';

    const btn = form.querySelector('[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Done!';
    emailInput.value = '';
    await new Promise(r => setTimeout(r, 2000));
    btn.disabled = false;
    btn.textContent = 'Book Your Free Pilot';
  });
}

/* ── Helpers ─────────────────────────────────────────────── */
function isValidEmail(val) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
}

/* ── Init ────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadI18n('en');
  initMobileNav();
  initAccordion();
  initContactForm();
  initCtaEmailForm();
});
