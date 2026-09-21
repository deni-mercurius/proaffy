/* ============================================================
   ProAffy - main.js
   Handles: mobile nav
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

/* ── Init ────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initMobileNav();
});
