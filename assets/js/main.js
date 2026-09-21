/* ============================================================
   ProAffy - main.js
   Handles: mobile nav, form submission
   ============================================================ */

/* ── Form config ─────────────────────────────────────────── */
/* Until FORM_ACCESS_KEY holds a real key, neither form claims to have sent
   anything. It says so and offers the email address instead. A form that
   reports success and drops the lead is worse than no form at all. */
const FORM_ENDPOINT   = 'https://api.web3forms.com/submit';
const FORM_ACCESS_KEY = 'WEB3FORMS_ACCESS_KEY_PLACEHOLDER';
const FALLBACK_EMAIL  = 'info@proaffy.com';

function formIsConfigured() {
  return FORM_ACCESS_KEY.indexOf('PLACEHOLDER') === -1;
}

async function postForm(fields) {
  const res = await fetch(FORM_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(Object.assign({ access_key: FORM_ACCESS_KEY }, fields))
  });

  let data = {};
  try {
    data = await res.json();
  } catch (_) {
    /* a non-JSON response is still a failure; fall through to the check */
  }

  if (!res.ok || data.success === false) {
    throw new Error(data.message || 'Submission failed (' + res.status + ')');
  }
  return data;
}

/* Writes a message into a status element. Builds the optional mailto link as a
   node rather than markup, so nothing the visitor typed can reach innerHTML. */
function writeStatus(el, msg, type, withFallback) {
  el.textContent = '';
  el.className = 'form__status form__status--' + type;
  el.style.display = 'block';
  el.appendChild(document.createTextNode(msg));

  if (withFallback) {
    el.appendChild(document.createTextNode(' '));
    const link = document.createElement('a');
    link.href = 'mailto:' + FALLBACK_EMAIL;
    link.textContent = FALLBACK_EMAIL;
    el.appendChild(link);
  }
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

/* ── Contact Form ────────────────────────────────────────── */
function initContactForm() {
  const form = document.getElementById('contactForm');
  if (!form) return;

  const statusEl = document.getElementById('formStatus');
  const submitBtn = form.querySelector('[type="submit"]');
  const submitLabel = submitBtn ? submitBtn.textContent : 'Send';

  form.addEventListener('submit', async e => {
    e.preventDefault();

    const firstName = form.firstName.value.trim();
    const lastName  = form.lastName.value.trim();
    const email     = form.email.value.trim();
    const company   = form.company ? form.company.value.trim() : '';
    const message   = form.message ? form.message.value.trim() : '';

    if (!firstName || !lastName) {
      writeStatus(statusEl, 'Please enter your first and last name.', 'err', false);
      return;
    }
    if (!isValidEmail(email)) {
      writeStatus(statusEl, 'Please enter a valid email address.', 'err', false);
      return;
    }

    if (!formIsConfigured()) {
      writeStatus(statusEl,
        'This form is not connected yet, so nothing was sent. Please email us at',
        'err', true);
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';

    try {
      await postForm({
        subject: 'Free pilot request from proaffy.com',
        from_name: firstName + ' ' + lastName,
        firstName: firstName,
        lastName: lastName,
        email: email,
        company: company,
        message: message
      });
      writeStatus(statusEl,
        'Thank you. We will be in touch within one business day.', 'ok', false);
      form.reset();
    } catch (err) {
      writeStatus(statusEl,
        'That did not send. Please try again, or email us at', 'err', true);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = submitLabel;
    }
  });
}

/* ── CTA Email Form ──────────────────────────────────────── */
function initCtaEmailForm() {
  const form = document.getElementById('ctaEmailForm');
  if (!form) return;

  const emailInput = form.querySelector('input[type="email"]');
  const btn = form.querySelector('[type="submit"]');
  const btnLabel = btn ? btn.textContent : 'Send';

  /* This form ships without a status element, so give it one. */
  let statusEl = form.querySelector('.form__status');
  if (!statusEl) {
    statusEl = document.createElement('p');
    statusEl.className = 'form__status';
    statusEl.setAttribute('role', 'alert');
    statusEl.setAttribute('aria-live', 'polite');
    statusEl.style.display = 'none';
    form.appendChild(statusEl);
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();

    const email = emailInput.value.trim();
    if (!isValidEmail(email)) {
      emailInput.setAttribute('aria-invalid', 'true');
      writeStatus(statusEl, 'Please enter a valid email address.', 'err', false);
      return;
    }
    emailInput.removeAttribute('aria-invalid');

    if (!formIsConfigured()) {
      writeStatus(statusEl,
        'This form is not connected yet, so nothing was sent. Please email us at',
        'err', true);
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Sending...';

    try {
      await postForm({
        subject: 'Free pilot request from proaffy.com',
        from_name: email,
        email: email
      });
      writeStatus(statusEl,
        'Thank you. We will be in touch within one business day.', 'ok', false);
      emailInput.value = '';
    } catch (err) {
      writeStatus(statusEl,
        'That did not send. Please try again, or email us at', 'err', true);
    } finally {
      btn.disabled = false;
      btn.textContent = btnLabel;
    }
  });
}

/* ── Helpers ─────────────────────────────────────────────── */
function isValidEmail(val) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
}

/* ── Init ────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initMobileNav();
  initContactForm();
  initCtaEmailForm();
});
