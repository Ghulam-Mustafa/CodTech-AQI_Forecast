let forecastChart, historyChart;

async function loadAll() {
  const city = document.getElementById("city-input").value.trim();
  if (!city) return;
  await Promise.all([loadCurrent(city), loadForecast(city), loadHistory(city), loadAlerts(city)]);
}

async function loadCurrent(city) {
  const res = await fetch(`/api/current?city=${encodeURIComponent(city)}`);
  const el = document.getElementById("current-card");
  if (!res.ok) {
    document.getElementById("aqi-advisory").textContent = "No data yet — seed and train the model first (see README).";
    return;
  }
  const data = await res.json();
  document.getElementById("aqi-value").textContent = Math.round(data.aqi);
  document.getElementById("aqi-value").style.color = data.color;
  const catEl = document.getElementById("aqi-category");
  catEl.textContent = data.category;
  catEl.style.background = data.color;
  document.getElementById("aqi-advisory").textContent = data.advisory;
  document.getElementById("dominant-pollutant").textContent = data.dominant_pollutant
    ? `Dominant pollutant: ${data.dominant_pollutant.toUpperCase()}`
    : "";
  document.getElementById("reading-timestamp").textContent = `Last updated: ${new Date(data.timestamp).toLocaleString()}`;
}

async function loadForecast(city) {
  const res = await fetch(`/api/forecast?city=${encodeURIComponent(city)}&days=7`);
  if (!res.ok) return;
  const data = await res.json();
  const labels = data.forecast.map(d => d.date);
  const values = data.forecast.map(d => d.predicted_aqi);
  const lower = data.forecast.map(d => d.lower_bound);
  const upper = data.forecast.map(d => d.upper_bound);
  const colors = data.forecast.map(d => d.color);

  if (forecastChart) forecastChart.destroy();
  const ctx = document.getElementById("forecast-chart");
  forecastChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Upper bound",
          data: upper,
          borderColor: "transparent",
          backgroundColor: "rgba(77,163,255,0.12)",
          fill: "+1",
          pointRadius: 0,
        },
        {
          label: "Lower bound",
          data: lower,
          borderColor: "transparent",
          backgroundColor: "rgba(77,163,255,0.12)",
          fill: false,
          pointRadius: 0,
        },
        {
          label: "Predicted AQI",
          data: values,
          borderColor: "#4da3ff",
          backgroundColor: colors,
          pointBackgroundColor: colors,
          pointRadius: 5,
          tension: 0.3,
        },
      ],
    },
    options: {
      plugins: { legend: { labels: { color: "#e8e9ee" } } },
      scales: {
        x: { ticks: { color: "#8b8fa3" }, grid: { color: "#262a36" } },
        y: { ticks: { color: "#8b8fa3" }, grid: { color: "#262a36" } },
      },
    },
  });
}

async function loadHistory(city) {
  const res = await fetch(`/api/history?city=${encodeURIComponent(city)}&days=30`);
  if (!res.ok) return;
  const data = await res.json();
  const labels = data.map(d => new Date(d.timestamp).toLocaleDateString());
  const values = data.map(d => d.aqi);

  if (historyChart) historyChart.destroy();
  const ctx = document.getElementById("history-chart");
  historyChart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets: [{ label: "AQI", data: values, borderColor: "#ff7e00", pointRadius: 0, tension: 0.25 }] },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8b8fa3", maxTicksLimit: 8 }, grid: { color: "#262a36" } },
        y: { ticks: { color: "#8b8fa3" }, grid: { color: "#262a36" } },
      },
    },
  });
}

async function loadAlerts(city) {
  const res = await fetch(`/api/alerts?city=${encodeURIComponent(city)}`);
  const list = document.getElementById("alerts-list");
  list.innerHTML = "";
  if (!res.ok) return;
  const data = await res.json();
  if (data.length === 0) {
    list.innerHTML = '<li class="empty">No alerts triggered recently.</li>';
    return;
  }
  data.forEach(a => {
    const li = document.createElement("li");
    li.textContent = `${a.forecast_date} — ${a.category} (AQI ${a.predicted_aqi}): ${a.message}`;
    list.appendChild(li);
  });
}

document.getElementById("load-btn").addEventListener("click", loadAll);

document.getElementById("subscribe-btn").addEventListener("click", async () => {
  const email = document.getElementById("email-input").value.trim();
  const city = document.getElementById("city-input").value.trim();
  const threshold = parseInt(document.getElementById("threshold-input").value, 10);
  const status = document.getElementById("subscribe-status");
  if (!email) { status.textContent = "Enter an email first."; return; }
  const res = await fetch("/api/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, city, threshold }),
  });
  status.textContent = res.ok ? "Subscribed!" : "Something went wrong.";
});

loadAll();
