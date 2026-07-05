const form = document.querySelector("#search-form");
const input = document.querySelector("#location-input");
const statusBox = document.querySelector("#status");
const content = document.querySelector("#weather-content");
const quickButtons = document.querySelectorAll("[data-city]");

const iconForCode = (code) => {
  if (code === 0) return "☀️";
  if ([1, 2].includes(code)) return "🌤️";
  if (code === 3) return "☁️";
  if ([45, 48].includes(code)) return "🌫️";
  if ([51, 53, 55, 56, 57].includes(code)) return "🌦️";
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return "🌧️";
  if ([71, 73, 75, 77, 85, 86].includes(code)) return "🌨️";
  if ([95, 96, 99].includes(code)) return "⛈️";
  return "🌡️";
};

const hourFromIso = (isoTime) => Number(isoTime.slice(11, 13));
const formatTime = (isoTime) => isoTime.slice(11, 16);

function setLoading(location) {
  content.hidden = true;
  statusBox.hidden = false;
  statusBox.classList.remove("error");
  statusBox.innerHTML =
    '<span class="spinner" aria-hidden="true"></span>' +
    `<span>${escapeHtml(location)}의 하늘을 살펴보고 있어요…</span>`;
}

function setError(message) {
  content.hidden = true;
  statusBox.hidden = false;
  statusBox.classList.add("error");
  statusBox.textContent = message;
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function renderCurrent(data) {
  const { location, current } = data;
  const detail = [location.admin1, location.country].filter(Boolean).join(", ");

  document.querySelector("#location-name").textContent = location.name;
  document.querySelector("#location-detail").textContent = detail;
  document.querySelector("#updated-time").textContent =
    `${formatTime(current.time)} 기준 · ${location.timezone}`;
  document.querySelector("#weather-icon").textContent = iconForCode(
    current.weatherCode,
  );
  document.querySelector("#current-temperature").textContent =
    `${Math.round(current.temperature)}°`;
  document.querySelector("#current-description").textContent =
    current.description;
  document.querySelector("#feels-like").textContent =
    `체감온도 ${Math.round(current.apparentTemperature)}°`;
  document.querySelector("#current-humidity").textContent =
    `${current.humidity}%`;
  document.querySelector("#current-wind").textContent =
    `${current.windSpeed} ${data.units.windSpeed}`;
  document.querySelector("#current-rain").textContent =
    `${current.precipitation} mm`;
}

function renderChart(hourly) {
  const width = 760;
  const height = 290;
  const padding = { top: 26, right: 26, bottom: 42, left: 42 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const temperatures = hourly.map((item) => item.temperature);
  const minimum = Math.floor(Math.min(...temperatures) - 2);
  const maximum = Math.ceil(Math.max(...temperatures) + 2);
  const range = Math.max(maximum - minimum, 1);
  const x = (index) =>
    padding.left + (index / Math.max(hourly.length - 1, 1)) * chartWidth;
  const y = (temperature) =>
    padding.top + ((maximum - temperature) / range) * chartHeight;
  const rainY = (probability) =>
    padding.top + chartHeight - (probability / 100) * chartHeight * 0.42;

  const linePoints = hourly
    .map((item, index) => `${x(index)},${y(item.temperature)}`)
    .join(" ");
  const areaPoints =
    `${padding.left},${padding.top + chartHeight} ` +
    `${linePoints} ${padding.left + chartWidth},${padding.top + chartHeight}`;

  const grid = [0, 0.25, 0.5, 0.75, 1]
    .map((ratio) => {
      const gridY = padding.top + ratio * chartHeight;
      const label = Math.round(maximum - ratio * range);
      return `
        <line x1="${padding.left}" y1="${gridY}" x2="${width - padding.right}"
          y2="${gridY}" stroke="#dce8f2" stroke-dasharray="3 5" />
        <text x="${padding.left - 10}" y="${gridY + 4}" text-anchor="end"
          fill="#8294a5" font-size="11">${label}°</text>`;
    })
    .join("");

  const bars = hourly
    .map((item, index) => {
      const barWidth = Math.max(chartWidth / hourly.length - 5, 4);
      const barY = rainY(item.precipitationProbability);
      return `<rect x="${x(index) - barWidth / 2}" y="${barY}"
        width="${barWidth}" height="${padding.top + chartHeight - barY}"
        rx="3" fill="#86c9ff" opacity="0.36" />`;
    })
    .join("");

  const labels = hourly
    .map((item, index) => {
      if (index % 3 !== 0 && index !== hourly.length - 1) return "";
      const hour = hourFromIso(item.time);
      return `<text x="${x(index)}" y="${height - 14}" text-anchor="middle"
        fill="#8294a5" font-size="11">${String(hour).padStart(2, "0")}시</text>`;
    })
    .join("");

  const points = hourly
    .map(
      (item, index) => `
        <circle cx="${x(index)}" cy="${y(item.temperature)}" r="3.5"
          fill="#ffffff" stroke="#246bfd" stroke-width="2">
          <title>${formatTime(item.time)} · ${item.temperature}° · 강수 ${item.precipitationProbability}%</title>
        </circle>`,
    )
    .join("");

  document.querySelector("#weather-chart").innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" aria-label="오늘 시간별 기온과 강수확률 그래프">
      <defs>
        <linearGradient id="temperature-area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#4b8dff" stop-opacity="0.28" />
          <stop offset="100%" stop-color="#4b8dff" stop-opacity="0" />
        </linearGradient>
      </defs>
      ${grid}
      ${bars}
      <polygon points="${areaPoints}" fill="url(#temperature-area)" />
      <polyline points="${linePoints}" fill="none" stroke="#246bfd"
        stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
      ${points}
      ${labels}
    </svg>`;
}

function renderHourly(hourly, currentTime) {
  const currentHour = hourFromIso(currentTime);
  document.querySelector("#hourly-list").innerHTML = hourly
    .map((item) => {
      const hour = hourFromIso(item.time);
      const isNow = hour === currentHour;
      return `
        <div class="hour ${isNow ? "now" : ""}">
          <p class="hour-time">${isNow ? "지금" : `${String(hour).padStart(2, "0")}시`}</p>
          <span class="hour-icon" title="${escapeHtml(item.description)}">${iconForCode(item.weatherCode)}</span>
          <p class="hour-temp">${Math.round(item.temperature)}°</p>
          <p class="hour-rain">💧 ${item.precipitationProbability}%</p>
        </div>`;
    })
    .join("");
}

function renderWeather(data) {
  renderCurrent(data);
  renderChart(data.hourly);
  renderHourly(data.hourly, data.current.time);
  statusBox.hidden = true;
  content.hidden = false;
}

async function loadWeather(location) {
  setLoading(location);
  try {
    const response = await fetch(
      `/api/weather?location=${encodeURIComponent(location)}`,
    );
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "날씨를 불러오지 못했습니다.");
    renderWeather(data);
  } catch (error) {
    setError(error.message || "네트워크 연결을 확인해 주세요.");
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const location = input.value.trim();
  if (location) loadWeather(location);
});

quickButtons.forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.city;
    loadWeather(button.dataset.city);
  });
});

loadWeather(input.value);
