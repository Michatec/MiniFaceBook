document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.lang-select').forEach(function(el) {
    el.addEventListener('click', function(e) {
      e.preventDefault();
      document.cookie = "lang=" + this.dataset.lang + ";path=/";
      location.reload();
    });
  });
});