// Multi-step assessment: shows one step at a time and checks every question is answered.
(function () {
  var form = document.getElementById('assessmentForm');
  if (!form) return;
  var panels = Array.prototype.slice.call(form.querySelectorAll('.step-panel'));
  var label = document.getElementById('stepLabel'), fill = document.getElementById('stepFill');
  var back = document.getElementById('btnBack'), next = document.getElementById('btnNext');
  var submit = document.getElementById('btnSubmit'), err = document.getElementById('stepError');
  var current = 0;

  function show(i) {
    current = i;
    panels.forEach(function (p, idx) { p.classList.toggle('d-none', idx !== i); });
    label.textContent = 'Step ' + (i + 1) + ' of ' + panels.length + ': ' + panels[i].dataset.title;
    fill.style.width = ((i + 1) / panels.length * 100) + '%';
    back.style.visibility = i === 0 ? 'hidden' : 'visible';
    var last = i === panels.length - 1;
    next.classList.toggle('d-none', last);
    submit.classList.toggle('d-none', !last);
    err.classList.add('d-none');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function validate(i) {
    var ok = true;
    panels[i].querySelectorAll('.question').forEach(function (q) {
      var answered = q.querySelector('input:checked') !== null;
      q.classList.toggle('missing', !answered);
      if (!answered) ok = false;
    });
    err.classList.toggle('d-none', ok);
    return ok;
  }

  next.addEventListener('click', function () { if (validate(current)) show(current + 1); });
  back.addEventListener('click', function () { if (current > 0) show(current - 1); });
  form.addEventListener('change', function (e) {
    var q = e.target.closest && e.target.closest('.question');
    if (q) q.classList.remove('missing');
  });
  form.addEventListener('submit', function (e) {
    for (var i = 0; i < panels.length; i++) {
      if (!validate(i)) { e.preventDefault(); show(i); validate(i); return; }
    }
    submit.disabled = true;             // avoid double submission
    submit.textContent = 'Analysing...';
  });
  show(0);
})();
