function reloadEvents() {
    fetch(apiEventsUrl)
      .then(r => r.json())
      .then(events => {
        let tbody = document.getElementById('events-tbody');
        tbody.innerHTML = "";
        for (let e of events) {
          let tr = document.createElement('tr');
          tr.innerHTML = `<td>${e.timestamp}</td><td>${e.message}</td>`;
          tbody.appendChild(tr);
        }
      });
}

setInterval(reloadEvents, 10000);
window.onload = reloadEvents;