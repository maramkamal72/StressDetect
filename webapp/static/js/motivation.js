// Shows the animated motivation pop-up after an assessment, with confetti for good news.
(function () {
  var element = document.getElementById('motivationModal');
  if (!element || typeof bootstrap === 'undefined') return;
  var COLOURS = ['#0D9488', '#115E59', '#0F172A', '#CCFBF1'];   // brand colours only
  function launchConfetti(layer) {
    if (!layer || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    for (var i = 0; i < 46; i++) {
      var piece = document.createElement('span'), size = 6 + Math.random() * 7;
      piece.className = 'confetti-piece';
      piece.style.left = Math.random() * 100 + '%';
      piece.style.width = size + 'px';
      piece.style.height = size * (0.6 + Math.random()) + 'px';
      piece.style.background = COLOURS[i % COLOURS.length];
      piece.style.animationDuration = 2.4 + Math.random() * 1.8 + 's';
      piece.style.animationDelay = Math.random() * 0.7 + 's';
      layer.appendChild(piece);
    }
  }
  var kind = element.getAttribute('data-kind');
  element.addEventListener('shown.bs.modal', function () {
    if (kind === 'improved' || kind === 'first') launchConfetti(element.querySelector('.confetti-layer'));
  });
  element.addEventListener('hidden.bs.modal', function () {      // remove ?new=1 so a refresh does not repeat it
    if (window.history && window.history.replaceState) {
      var url = new URL(window.location.href);
      url.searchParams.delete('new');
      window.history.replaceState({}, '', url.pathname + url.search);
    }
  });
  new bootstrap.Modal(element).show();
})();
