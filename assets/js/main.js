/* ============================================================
   ProAffy - main.js
   Handles: mobile nav, the cost model on the homepage
   ============================================================ */

/* The forms are not here, on purpose.

   They post natively to the form endpoint and it redirects back to the page
   with #sent, which :target turns into the confirmation panel. That means no
   fetch, no JSON, and no CORS: a form POST is a navigation, not a cross-origin
   request. An earlier version used fetch with Content-Type: application/json,
   which forces a CORS preflight that the endpoint rejects, so nothing ever
   sent.

   It also means both forms work with JavaScript disabled, which the FAQ on
   this site already manages by using a native <details> element. Validation is
   the browser's: the fields carry required and type="email", and the form no
   longer sets novalidate. */

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

/* ── The model ───────────────────────────────────────────── */
/* Every figure it prints comes from the three inputs. Nothing here carries an
   industry average, because we do not have a sourced one and will not invent
   it. The markup already contains the answers for the default inputs, so with
   scripting off the page still shows a complete, correct worked example. */
function initModel() {
  const root = document.getElementById('model');
  if (!root) return;

  const leads  = document.getElementById('leads');
  const fast   = document.getElementById('fast');
  const ticket = document.getElementById('ticket');
  const slow   = document.getElementById('slow');
  const out    = { 20: document.getElementById('out20'),
                   10: document.getElementById('out10'),
                    5: document.getElementById('out5') };
  const question = root.querySelector('.model__question');
  if (!leads || !fast || !ticket || !slow || !question) return;

  const money = n => '$' + Math.round(n).toLocaleString('en-US');
  const num = el => {
    const v = parseInt(el.value, 10);
    return Number.isFinite(v) && v >= 0 ? v : 0;
  };

  function update() {
    const missed = Math.max(0, num(leads) - num(fast));
    const value = num(ticket);
    slow.textContent = missed;
    for (const share of [20, 10, 5]) {
      if (out[share]) out[share].textContent = money(missed / share * value);
    }
    question.textContent =
      'How many of those ' + missed + ' would have booked if somebody had ' +
      'answered straight away? Nobody can tell you that, so here it is three ways.';
  }

  /* A lead answered late cannot exceed the leads that arrived. */
  function clamp() {
    if (num(fast) > num(leads)) fast.value = num(leads);
  }

  for (const el of [leads, fast, ticket]) {
    el.addEventListener('input', () => { clamp(); update(); });
  }
  update();
}

/* ── Init ────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initMobileNav();
  initModel();
});
