document.addEventListener("DOMContentLoaded", function () {
    var hash = window.location.hash;
    if (hash) {
      var tabTrigger = document.querySelector('#adminTab button[data-bs-target="' + hash + '"]');
      if (tabTrigger) {
        var tab = new bootstrap.Tab(tabTrigger);
        tab.show();
      }
    }

    var triggerTabList = [].slice.call(document.querySelectorAll('#adminTab button'));
    triggerTabList.forEach(function (triggerEl) {
      triggerEl.addEventListener('shown.bs.tab', function (event) {
        var target = triggerEl.getAttribute('data-bs-target');
        if (target) {
          history.replaceState(null, null, target);
        }
      });
    });
  });