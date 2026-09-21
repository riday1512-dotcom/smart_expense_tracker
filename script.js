// Smart Expense Tracker — auth page interactions
// Password show/hide, live strength meter, and a submit loading state.
// Every enhancement here is progressive: the forms work fine without JS.

document.addEventListener('DOMContentLoaded', function () {

  // Password show/hide is handled by the inline <script> at the
  // bottom of each page (kept out of this file so it can't fail
  // to load) — see login.html / register.html.

  // ---- password strength meter (register page only) -----------------
  var pwInput = document.getElementById('password');
  var meter = document.getElementById('strength-meter');
  var label = document.getElementById('strength-label');

  if (pwInput && meter && label) {
    var bars = meter.querySelectorAll('span');
    var levels = [
      { text: 'Use 8+ characters with a number and a symbol', className: '' },
      { text: 'Weak — try adding a number or symbol', className: 'weak' },
      { text: 'Good — a longer password is even safer', className: 'good' },
      { text: 'Strong password', className: 'strong' }
    ];

    pwInput.addEventListener('input', function () {
      var value = pwInput.value;
      var score = 0;

      if (value.length >= 8) score++;
      if (/[0-9]/.test(value) && /[a-zA-Z]/.test(value)) score++;
      if (/[^a-zA-Z0-9]/.test(value) && value.length >= 10) score++;

      if (value.length === 0) score = 0;

      bars.forEach(function (bar, i) {
        bar.classList.toggle('filled', i < score + (value.length > 0 ? 1 : 0));
      });

      var level = levels[Math.min(score + (value.length > 0 ? 1 : 0), levels.length - 1)];
      if (value.length === 0) level = levels[0];

      meter.className = 'strength-meter ' + level.className;
      label.textContent = level.text;
    });
  }

  // ---- submit loading state ------------------------------------------
  document.querySelectorAll('form').forEach(function (form) {
    form.addEventListener('submit', function () {
      var btn = form.querySelector('.submit-btn');
      if (!btn || btn.classList.contains('is-loading')) return;
      btn.classList.add('is-loading');
      btn.querySelector('.btn-label').hidden = true;
      btn.querySelector('.btn-spinner').hidden = false;
      btn.disabled = true;
    });
  });

});