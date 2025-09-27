function setTheme(mode, save=true) {
    document.body.classList.remove('light-mode', 'dark-mode');
    document.body.classList.add(mode + '-mode');
    document.getElementById('theme-icon').className = mode === 'dark' ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
    document.getElementById('theme-label').textContent = mode === 'dark' ? 'Dark-Mode' : 'Light-Mode';
    if(save) document.cookie = "theme=" + mode + ";path=/;max-age=31536000";
}
function getCookie(name) {
    let v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
    return v ? v[2] : null;
}

function systemPrefersDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

document.addEventListener('DOMContentLoaded', function() {
    let theme = getCookie('theme');
    if(!theme) theme = systemPrefersDark() ? 'dark' : 'light';
    setTheme(theme, false);
    document.getElementById('toggle-theme').onclick = function() {
        let newTheme = document.body.classList.contains('dark-mode') ? 'light' : 'dark';
        setTheme(newTheme);
    };
});