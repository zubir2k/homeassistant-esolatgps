/**
 * eSolat GPS Card
 * A prayer-time card for the eSolat GPS integration
 * (https://github.com/zubir2k/homeassistant-esolatgps)
 *
 * Inspired by Iman Pro (sky themes), Mosque Screen Card (countdown ring)
 * and Malaysia Prayer Times (clean list).
 *
 * MIT License
 */

const CARD_VERSION = "0.2.6";
const TZ = "Asia/Kuala_Lumpur";

const PRAYERS = [
  { key: "imsak", ms: "Imsak", en: "Imsak", icon: "mdi:weather-night", extra: true },
  { key: "subuh", ms: "Subuh", en: "Fajr", icon: "mdi:weather-sunset-up" },
  { key: "syuruk", ms: "Syuruk", en: "Sunrise", icon: "mdi:white-balance-sunny", ref: true },
  { key: "isyraq", ms: "Isyraq", en: "Ishraq", icon: "mdi:weather-sunny", extra: true, optional: true },
  { key: "dhuha", ms: "Dhuha", en: "Duha", icon: "mdi:weather-partly-cloudy", extra: true, optional: true },
  { key: "zohor", ms: "Zohor", en: "Dhuhr", icon: "mdi:weather-sunny" },
  { key: "asar", ms: "Asar", en: "Asr", icon: "mdi:weather-hazy" },
  { key: "maghrib", ms: "Maghrib", en: "Maghrib", icon: "mdi:weather-sunset-down" },
  { key: "isyak", ms: "Isyak", en: "Isha", icon: "mdi:weather-night" },
];

const T = {
  ms: {
    now: "Waktu Sekarang",
    next: "Seterusnya",
    in: "lagi",
    tomorrow: "Esok",
    jumaat: "Jumaat",
    home: "Rumah",
    outside: "Di luar Malaysia",
    unavailable: "Waktu solat tidak tersedia",
    stale: "Waktu solat belum dikemas kini",
    noSensor: "Sensor tidak dijumpai",
    h: "j",
    m: "m",
    s: "s",
    adhan: "Telah masuk waktu",
  },
  en: {
    now: "Current",
    next: "Next",
    in: "to go",
    tomorrow: "Tomorrow",
    jumaat: "Jumu'ah",
    home: "Home",
    outside: "Outside Malaysia",
    unavailable: "Prayer times unavailable",
    stale: "Prayer times out of date",
    noSensor: "Sensor not found",
    h: "h",
    m: "m",
    s: "s",
    adhan: "It is now time for",
  },
};

/* Sky gradients per prayer period (Iman-Pro-style "sky" theme). */
const SKY = {
  isyak: ["#0b1026", "#1b2350", "#2c2f6b"],
  imsak: ["#0d1330", "#23295e", "#3d3a78"],
  subuh: ["#1d2b5a", "#5b4b8a", "#d98aa0"],
  syuruk: ["#2f5f94", "#d98a45", "#c9733a"],
  isyraq: ["#2f6db5", "#4f8fcf", "#c98a45"],
  dhuha: ["#1f6cb8", "#3f8ad3", "#5d9fdc"],
  zohor: ["#1a66b8", "#3489d6", "#5a9fe0"],
  asar: ["#255f9e", "#c98543", "#b8702f"],
  maghrib: ["#2b1d4f", "#b0436b", "#f28c4b"],
};

const PALETTES = {
  emerald: { bg: "linear-gradient(160deg,#0a2e22,#0f3d2e 55%,#123f30)", accent: "#d4af37", text: "#f4efe0", muted: "rgba(244,239,224,.62)", row: "rgba(255,255,255,.05)", rowActive: "rgba(212,175,55,.18)" },
  midnight: { bg: "linear-gradient(160deg,#0b1430,#13204a 60%,#182a5c)", accent: "#e6c87a", text: "#eef1fb", muted: "rgba(238,241,251,.6)", row: "rgba(255,255,255,.05)", rowActive: "rgba(230,200,122,.18)" },
  turquoise: { bg: "linear-gradient(160deg,#06302f,#0b4645 60%,#0f5553)", accent: "#f0b860", text: "#effaf8", muted: "rgba(239,250,248,.62)", row: "rgba(255,255,255,.06)", rowActive: "rgba(240,184,96,.2)" },
  sable: { bg: "linear-gradient(160deg,#2a1a10,#3a2516 60%,#45301d)", accent: "#f2a93b", text: "#fbf3e8", muted: "rgba(251,243,232,.6)", row: "rgba(255,255,255,.05)", rowActive: "rgba(242,169,59,.2)" },
  slate: { bg: "linear-gradient(160deg,#1e2328,#2a3036 60%,#333a41)", accent: "#e9dca6", text: "#f6f7f8", muted: "rgba(246,247,248,.62)", row: "rgba(255,255,255,.06)", rowActive: "rgba(233,220,166,.2)" },
};

/* ---------- time helpers (always Malaysia time, whatever the browser zone) ---------- */

const safeTz = (tz) => {
  try { new Intl.DateTimeFormat("en-GB", { timeZone: tz }); return tz; } catch (e) { return TZ; }
};

const fmtParts = (date, opts, tz = TZ) =>
  Object.fromEntries(
    new Intl.DateTimeFormat("en-GB", { timeZone: tz, ...opts })
      .formatToParts(date)
      .map((p) => [p.type, p.value])
  );

const myDateKey = (date, tz = TZ) => {
  const p = fmtParts(date, { year: "numeric", month: "2-digit", day: "2-digit" }, tz);
  return `${p.year}-${p.month}-${p.day}`;
};

const fmtTime = (date, hour12, tz = TZ) => {
  const s = new Intl.DateTimeFormat(hour12 ? "en-US" : "en-GB", {
    timeZone: tz,
    hour: hour12 ? "numeric" : "2-digit",
    minute: "2-digit",
    hour12,
  }).format(date);
  return s.replace(/\s?(AM|PM)/i, (m) => " " + m.trim().toUpperCase());
};

const fmtClock = (date, hour12, tz = TZ) => {
  const p = fmtParts(date, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12 }, tz);
  const ap = p.dayPeriod ? p.dayPeriod.toUpperCase() : "";
  const hh = hour12 ? String(parseInt(p.hour, 10)) : p.hour;
  return { hm: `${hh}:${p.minute}`, s: p.second, ap };
};

const fmtGregorian = (date, lang, tz = TZ) =>
  new Intl.DateTimeFormat(lang === "ms" ? "ms-MY" : "en-GB", {
    timeZone: tz,
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);

const isFridayMY = (date, tz = TZ) => fmtParts(date, { weekday: "short" }, tz).weekday === "Fri";

const fmtCountdown = (ms, t, withSeconds) => {
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n) => String(n).padStart(2, "0");
  if (withSeconds) return h ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
  return h ? `${h}${t.h} ${m}${t.m}` : `${m}${t.m}`;
};

const escapeHtml = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ---------- moon phase from the Hijri day ---------- */
function moonSvg(day, color) {
  const d = Math.min(Math.max(parseInt(day, 10) || 1, 1), 30);
  const phase = d / 29.53; // 0 new → 0.5 full → 1 new
  const r = 40;
  const illum = phase <= 0.5 ? phase * 2 : (1 - phase) * 2; // 0..1
  const waxing = phase <= 0.5;
  const rx = Math.abs(1 - 2 * illum) * r;
  const sweepOuter = waxing ? 1 : 0;
  const sweepInner = illum > 0.5 ? (waxing ? 1 : 0) : waxing ? 0 : 1;
  const path = `M50,${50 - r} A${r},${r} 0 0,${sweepOuter} 50,${50 + r} A${rx},${r} 0 0,${sweepInner} 50,${50 - r} Z`;
  return `<svg viewBox="0 0 100 100" class="moon" aria-hidden="true">
    <circle cx="50" cy="50" r="${r}" fill="${color}" opacity=".08"/>
    <path d="${path}" fill="${color}" opacity=".35"/>
  </svg>`;
}

/* ===================================================================== */

class EsolatGpsCard extends HTMLElement {
  static getStubConfig(hass) {
    return { type: "custom:esolatgps-card", entity: "auto", theme: "sky", language: "ms" };
  }

  static getConfigForm() {
    return {
      schema: [
        {
          name: "entity",
          selector: { text: {} },
        },
        { name: "title", selector: { text: {} } },
        {
          type: "grid",
          name: "",
          schema: [
            {
              name: "theme",
              selector: {
                select: {
                  mode: "dropdown",
                  options: [
                    { value: "sky", label: "Sky (changes with the time of day)" },
                    { value: "emerald", label: "Emerald" },
                    { value: "midnight", label: "Midnight" },
                    { value: "turquoise", label: "Turquoise" },
                    { value: "sable", label: "Sable" },
                    { value: "slate", label: "Slate" },
                    { value: "ha", label: "Follow Home Assistant theme" },
                  ],
                },
              },
            },
            {
              name: "language",
              selector: { select: { mode: "dropdown", options: [{ value: "ms", label: "Bahasa Melayu" }, { value: "en", label: "English" }] } },
            },
            {
              name: "layout",
              selector: { select: { mode: "dropdown", options: [{ value: "auto", label: "Auto" }, { value: "full", label: "Full" }, { value: "compact", label: "Compact" }] } },
            },
            { name: "seconds_threshold", selector: { number: { min: 0, max: 180, mode: "box", unit_of_measurement: "min" } } },
          ],
        },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "hour12", selector: { boolean: {} } },
            { name: "show_clock", selector: { boolean: {} } },
            { name: "show_imsak", selector: { boolean: {} } },
            { name: "show_syuruk", selector: { boolean: {} } },
            { name: "show_isyraq_dhuha", selector: { boolean: {} } },
            { name: "show_moon", selector: { boolean: {} } },
            { name: "show_location", selector: { boolean: {} } },
            { name: "home_when_home", selector: { boolean: {} } },
          ],
        },
        { name: "height", selector: { text: {} } },
      ],
      computeLabel: (s) =>
        ({
          entity: "Sensor (auto, or e.g. sensor.esolat_home)",
          title: "Title (optional)",
          theme: "Theme",
          language: "Language",
          layout: "Layout",
          seconds_threshold: "Show seconds when next prayer is within",
          hour12: "12-hour time",
          show_clock: "Show live clock",
          show_imsak: "Show Imsak",
          show_syuruk: "Show Syuruk",
          show_isyraq_dhuha: "Show Isyraq & Dhuha",
          show_moon: "Show moon phase",
          show_location: "Show location",
          home_when_home: "Use Home times when user is home (auto)",
          height: "Fixed height (e.g. 420px, optional)",
        }[s.name] ?? s.name),
    };
  }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Invalid configuration");
    // Home Assistant shows a thrown error in place of the card, so fail loudly on typos.
    const oneOf = (key, allowed) => {
      if (config[key] !== undefined && !allowed.includes(config[key])) {
        throw new Error(`Invalid ${key}: "${config[key]}". Use one of: ${allowed.join(", ")}`);
      }
    };
    oneOf("theme", ["sky", "ha", ...Object.keys(PALETTES)]);
    oneOf("language", ["ms", "en"]);
    oneOf("layout", ["auto", "full", "compact"]);
    if (config.entity !== undefined && typeof config.entity !== "string") {
      throw new Error("entity must be a sensor entity id, or \"auto\"");
    }
    if (config.seconds_threshold !== undefined && !Number.isFinite(Number(config.seconds_threshold))) {
      throw new Error("seconds_threshold must be a number of minutes");
    }
    this._config = {
      entity: "auto",
      theme: "sky",
      language: "ms",
      layout: "compact",
      hour12: false,
      show_clock: false,
      show_imsak: false,
      show_syuruk: false,
      show_isyraq_dhuha: false,
      show_moon: false,
      show_location: false,
      home_when_home: false,
      seconds_threshold: 60,
      tap_action: "more-info",
      ...config,
    };
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    this._render();
  }

  set hass(hass) {
    // hass is replaced on every state change anywhere in the home. Only re-render
    // when something this card actually reads has changed (state objects are
    // replaced, not mutated, so a reference check is enough).
    const prev = this._hass;
    this._hass = hass;
    const id = this._entityId;
    if (
      prev && id && this._config &&
      prev.states[id] === hass.states[id] &&
      prev.states["sensor.esolatnow"] === hass.states["sensor.esolatnow"] &&
      (!this._personId || prev.states[this._personId] === hass.states[this._personId])
    ) {
      return;
    }
    this._render();
  }

  connectedCallback() {
    clearInterval(this._timer);
    this._timer = setInterval(() => this._tick(), 1000);
  }

  disconnectedCallback() {
    clearInterval(this._timer);
  }

  // Masonry view height, in units of 50px. Compact is roughly 230px, full roughly 500px.
  getCardSize() {
    return this._config?.layout === "compact" ? 5 : 10;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  /* ---------- data ---------- */

  _resolveEntity() {
    const hass = this._hass;
    const cfg = this._config;
    if (cfg.entity && cfg.entity !== "auto") return cfg.entity;

    // Remember which person entity belongs to this user, so we don't scan every
    // entity in Home Assistant on each update.
    let person = this._personId ? hass.states[this._personId] : undefined;
    if (!person) {
      const userName = hass.user?.name;
      const userId = hass.user?.id;
      person = Object.values(hass.states).find(
        (s) =>
          s.entity_id.startsWith("person.") &&
          (s.attributes.user_id === userId || s.attributes.friendly_name === userName)
      );
      this._personId = person?.entity_id;
    }
    if (person) {
      const sensorId = "sensor.esolat_" + person.entity_id.split(".")[1];
      const sensor = hass.states[sensorId];
      const usable = sensor && !["unknown", "unavailable"].includes(sensor.state) && sensor.attributes.subuh;
      if (usable && !(cfg.home_when_home && person.state === "home")) return sensorId;
    }
    return "sensor.esolat_home";
  }

  _schedule(attrs) {
    const show = (p) => {
      if (p.key === "imsak") return this._config.show_imsak;
      if (p.key === "syuruk") return this._config.show_syuruk;
      if (p.key === "isyraq" || p.key === "dhuha") return this._config.show_isyraq_dhuha;
      return true;
    };
    return PRAYERS.filter((p) => attrs[p.key])
      .map((p) => ({ ...p, time: new Date(attrs[p.key]), visible: show(p) }))
      .filter((p) => !isNaN(p.time));
  }

  /* Current / next across the full schedule (visible or not), like sensor.esolatnow. */
  _currentNext(schedule, now) {
    const core = schedule; // include Isyraq/Dhuha so it matches sensor.esolatnow
    let current = null;
    let next = null;
    let tomorrow = false;
    for (const p of core) {
      if (p.time <= now) current = p;
      else if (!next) next = p;
    }
    if (!current) {
      // After midnight, before Imsak → still Isyak (yesterday's)
      const isyak = core.find((p) => p.key === "isyak");
      current = isyak ? { ...isyak, time: new Date(isyak.time.getTime() - 86400000) } : null;
    }
    if (!next) {
      const first = core[0];
      next = first ? { ...first, time: new Date(first.time.getTime() + 86400000) } : null;
      tomorrow = true;
    }
    return { current, next, tomorrow };
  }

  _label(p, now) {
    const lang = this._config.language === "en" ? "en" : "ms";
    if (p.key === "zohor" && isFridayMY(now, this._tz || TZ)) return T[lang].jumaat;
    return p[lang];
  }

  /* ---------- rendering ---------- */

  _themeVars(currentKey) {
    const theme = this._config.theme;
    if (theme === "ha") {
      return `--esg-bg: var(--ha-card-background, var(--card-background-color));
        --esg-text: var(--primary-text-color); --esg-muted: var(--secondary-text-color);
        --esg-accent: var(--primary-color); --esg-row: var(--secondary-background-color);
        --esg-row-active: rgba(var(--rgb-primary-color, 3,169,244), .18);`;
    }
    if (theme === "sky") {
      const g = SKY[currentKey] || SKY.zohor;
      const day = ["syuruk", "isyraq", "dhuha", "zohor", "asar"].includes(currentKey);
      return `--esg-bg: linear-gradient(170deg, ${g[0]} 0%, ${g[1]} 55%, ${g[2]} 100%);
        --esg-text: #ffffff; --esg-muted: rgba(255,255,255,${day ? ".88" : ".72"});
        --esg-accent: ${day ? "#fff3c4" : "#ffd27a"};
        --esg-shadow: ${day ? "0 1px 3px rgba(0,0,0,.35)" : "none"};
        --esg-row: ${day ? "rgba(0,0,0,.14)" : "rgba(255,255,255,.08)"}; --esg-row-active: rgba(255,255,255,${day ? ".26" : ".2"});`;
    }
    const p = PALETTES[theme] || PALETTES.emerald;
    return `--esg-bg: ${p.bg}; --esg-text: ${p.text}; --esg-muted: ${p.muted};
      --esg-accent: ${p.accent}; --esg-row: ${p.row}; --esg-row-active: ${p.rowActive};`;
  }

  _render() {
    if (!this._config || !this._hass || !this.shadowRoot) return;
    const now = new Date();
    const cfg = this._config;
    const lang = cfg.language === "en" ? "en" : "ms";
    const t = T[lang];

    const entityId = this._resolveEntity();
    const stateObj = this._hass.states[entityId];
    const tz = (this._tz = safeTz(stateObj?.attributes?.timezone || TZ));
    const abroad = stateObj?.attributes?.flag === "outside_malaysia" || stateObj?.attributes?.outside_malaysia === true;
    const nowSensor = this._hass.states["sensor.esolatnow"];
    const hijri = nowSensor?.attributes?.hijri && nowSensor.attributes.hijri !== "unavailable" ? nowSensor.attributes.hijri : "";
    const hijriDay = hijri ? hijri.split(" ")[0] : "";

    // Build a signature so we only rebuild the DOM when the data changes
    const sig = JSON.stringify([entityId, stateObj?.state, stateObj?.last_updated, hijri, myDateKey(now, tz), cfg]);
    const status = this._status(stateObj, now);
    const schedule = status === "ok" ? this._schedule(stateObj.attributes) : [];
    const cn = status === "ok" ? this._currentNext(schedule, now) : {};
    const periodKey = cn.current?.key || "zohor";
    const sig2 = sig + periodKey + (cn.next?.key || "");

    if (sig2 === this._sig) return this._tick();
    this._sig = sig2;
    this._entityId = entityId;
    this._schedState = { schedule, status };

    const location = `${stateObj?.state ?? ""}`;
    const isHome = entityId === "sensor.esolat_home";

    let body;
    if (status !== "ok") {
      const msg =
        status === "missing" ? `${t.noSensor}: ${escapeHtml(entityId)}`
        : status === "outside" ? `${t.outside}${stateObj.state && stateObj.state !== "Outside Malaysia" ? " · " + escapeHtml(stateObj.state) : stateObj.attributes.location ? " · " + escapeHtml(stateObj.attributes.location) : ""}`
        : status === "stale" ? t.stale
        : t.unavailable;
      body = `<div class="notice"><ha-icon icon="mdi:alert-circle-outline"></ha-icon><span>${msg}</span></div>`;
    } else {
      const rows = schedule
        .filter((p) => p.visible)
        .map((p) => {
          const active = cn.current && p.key === cn.current.key && cn.current.time.getTime() === p.time.getTime();
          const isNext = !cn.tomorrow && cn.next && p.key === cn.next.key;
          const past = p.time <= now && !active;
          return `<div class="row ${active ? "active" : ""} ${isNext ? "upcoming" : ""} ${past ? "past" : ""} ${p.ref || p.extra ? "minor" : ""}">
            <ha-icon icon="${p.icon}"></ha-icon>
            <span class="name">${this._label(p, now)}</span>
            <span class="time">${fmtTime(p.time, cfg.hour12, tz)}</span>
          </div>`;
        })
        .join("");

      body = `
        <div class="hero">
          <div class="ring-wrap">
            <svg class="ring" viewBox="0 0 120 120">
              <circle class="track" cx="60" cy="60" r="54"/>
              <circle class="prog" cx="60" cy="60" r="54" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100"/>
            </svg>
            ${cfg.show_moon && hijriDay ? moonSvg(hijriDay, "currentColor") : ""}
            <div class="ring-inner">
              <div class="lbl">${t.next}</div>
              <div class="nname">${this._label(cn.next, now)}</div>
              <div class="cd" id="cd">--</div>
              <div class="ntime">${fmtTime(cn.next.time, cfg.hour12, tz)}</div>
            </div>
          </div>
          <div class="side">
            ${cfg.show_clock ? `<div class="clock"><span id="hm">--:--</span><span class="sec" id="sec"></span><span class="ap" id="ap"></span></div>` : ""}
            <div class="dates">
              <div>${escapeHtml(fmtGregorian(now, lang, tz))}</div>
              ${hijri ? `<div class="hijri">${escapeHtml(hijri)}</div>` : ""}
            </div>
            <div class="current-pill">
              <span class="dot"></span>${t.now}: <b>${cn.current ? this._label(cn.current, now) : "-"}</b>
            </div>
          </div>
        </div>
        <div class="list">${rows}</div>`;
    }

    const title = cfg.title ? `<div class="title">${escapeHtml(cfg.title)}</div>` : "";
    const loc =
      cfg.show_location && stateObj && status !== "missing"
        ? `<div class="loc"><ha-icon icon="${isHome ? "mdi:home-variant" : abroad ? "mdi:earth" : "mdi:crosshairs-gps"}"></ha-icon><span>${escapeHtml(isHome ? `${t.home} · ${location}` : location)}</span></div>${abroad && stateObj.attributes.method ? `<div class="loc src" title="${escapeHtml(stateObj.attributes.method)}"><span>Aladhan · ${escapeHtml(stateObj.attributes.method)}</span></div>` : ""}`
        : "";

    this.shadowRoot.innerHTML = `
      <style>${this._css()}</style>
      <ha-card class="layout-${cfg.layout}" style="${this._themeVars(periodKey)}${cfg.height ? `height:${escapeHtml(cfg.height)};` : ""}">
        <div class="bg"></div>
        <div class="content">
          ${title || loc ? `<div class="header">${title}${loc}</div>` : ""}
          ${body}
        </div>
      </ha-card>`;

    this.shadowRoot.querySelector("ha-card").addEventListener("click", (e) => {
      if (cfg.tap_action === "none") return;
      const ev = new Event("hass-more-info", { bubbles: true, composed: true });
      ev.detail = { entityId: this._entityId };
      this.dispatchEvent(ev);
    });

    this._cn = cn;
    this._tick();
  }

  _status(stateObj, now) {
    if (!stateObj) return "missing";
    const outside = stateObj.state === "Outside Malaysia" || stateObj.attributes.flag === "outside_malaysia";
    if (outside && !stateObj.attributes.subuh) return "outside";
    if (["unknown", "unavailable"].includes(stateObj.state) || !stateObj.attributes.subuh) return "unavailable";
    const subuh = new Date(stateObj.attributes.subuh);
    if (isNaN(subuh)) return "unavailable";
    const tz = this._tz || TZ;
    const today = myDateKey(now, tz);
    const yesterday = myDateKey(new Date(now.getTime() - 86400000), tz);
    const day = myDateKey(subuh, tz);
    // Allow yesterday's data for the first hour after midnight while the integration refreshes
    if (day !== today && !(day === yesterday && parseInt(fmtParts(now, { hour: "2-digit", hour12: false }, tz).hour, 10) < 1)) return "stale";
    return "ok";
  }

  _tick() {
    const root = this.shadowRoot;
    if (!root || !this._config) return;
    const now = new Date();
    const cfg = this._config;
    const t = T[cfg.language === "en" ? "en" : "ms"];

    if (cfg.show_clock) {
      const c = fmtClock(now, cfg.hour12, this._tz || TZ);
      const hm = root.getElementById("hm");
      if (hm) {
        hm.textContent = c.hm;
        root.getElementById("sec").textContent = c.s;
        root.getElementById("ap").textContent = c.ap;
      }
    }

    // The hass setter no longer re-renders on unrelated updates, so catch time-based
    // changes here (new day, or the one-hour grace period after midnight ending).
    const minute = Math.floor(now.getTime() / 60000);
    if (minute !== this._lastMinute) {
      this._lastMinute = minute;
      const tz = this._tz || TZ;
      const key = `${myDateKey(now, tz)}-${fmtParts(now, { hour: "2-digit", hour12: false }, tz).hour}`;
      if (this._clockKey && key !== this._clockKey) {
        this._clockKey = key;
        this._sig = null;
        return this._render();
      }
      this._clockKey = key;
    }

    const cn = this._cn;
    if (!cn || !cn.next) return;

    // Crossed into a new prayer period → re-render
    if (now >= cn.next.time) {
      this._sig = null;
      return this._render();
    }

    const remaining = cn.next.time - now;
    const withSec = remaining <= (Number(cfg.seconds_threshold) || 0) * 60000;
    const cd = root.getElementById("cd");
    if (cd) cd.textContent = fmtCountdown(remaining, t, withSec);

    const prog = root.querySelector(".prog");
    if (prog && cn.current) {
      const span = cn.next.time - cn.current.time;
      const frac = span > 0 ? Math.min(1, Math.max(0, (now - cn.current.time) / span)) : 0;
      prog.setAttribute("stroke-dashoffset", String(100 - frac * 100));
    }
  }

  _css() {
    return `
      :host { display:block; }
      ha-card {
        position:relative; overflow:hidden; cursor:pointer;
        color:var(--esg-text); border:none; text-shadow:var(--esg-shadow, none);
        container-type:inline-size;
        min-height:100%;
      }
      .bg { position:absolute; inset:0; background:var(--esg-bg); transition:background 1s; }
      .content { position:relative; padding:18px 18px 16px; display:flex; flex-direction:column; gap:14px; height:100%; box-sizing:border-box; }
      .header { display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap; }
      .title { font-size:1.1rem; font-weight:600; letter-spacing:.2px; }
      .loc { display:flex; align-items:center; gap:6px; font-size:.82rem; color:var(--esg-muted);
             background:var(--esg-row); padding:4px 10px 4px 8px; border-radius:999px; max-width:100%; }
      .loc span { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      .loc ha-icon { --mdc-icon-size:16px; }
      .loc.src { font-size:.72rem; padding:3px 10px; opacity:.85; }

      .hero { display:flex; align-items:center; gap:20px; }
      .ring-wrap { position:relative; width:168px; height:168px; flex:0 0 auto; color:var(--esg-accent); }
      .ring { width:100%; height:100%; transform:rotate(-90deg); }
      .ring circle { fill:none; stroke-width:6; }
      .ring .track { stroke:var(--esg-row); }
      .ring .prog { stroke:var(--esg-accent); stroke-linecap:round; transition:stroke-dashoffset 1s linear; }
      .moon { position:absolute; inset:22px; width:calc(100% - 44px); height:calc(100% - 44px); }
      .ring-inner { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; color:var(--esg-text); }
      .lbl { font-size:.72rem; text-transform:uppercase; letter-spacing:1.4px; color:var(--esg-muted); }
      .nname { font-size:1.15rem; font-weight:600; margin-top:2px; }
      .cd { font-size:1.9rem; font-weight:700; font-variant-numeric:tabular-nums; line-height:1.15; color:var(--esg-accent); }
      .ntime { font-size:.85rem; color:var(--esg-muted); }

      .side { display:flex; flex-direction:column; gap:8px; min-width:0; }
      .clock { font-size:4.0rem; font-weight:300; line-height:1; font-variant-numeric:tabular-nums; letter-spacing:-1px; }
      .clock .sec { font-size:1.3rem; margin-left:4px; color:var(--esg-muted); letter-spacing:0; }
      .clock .ap { font-size:1.2rem; margin-left:6px; font-weight:500; letter-spacing:0; }
      .dates { font-size:.88rem; line-height:1.4; }
      .dates .hijri { color:var(--esg-accent); font-weight:500; }
      .current-pill { align-self:flex-start; font-size:.8rem; background:var(--esg-row); padding:5px 12px; border-radius:999px; display:flex; align-items:center; gap:6px; }
      .current-pill .dot { width:7px; height:7px; border-radius:50%; background:var(--esg-accent); box-shadow:0 0 0 3px rgba(255,255,255,.12); animation:pulse 2s infinite; }
      @keyframes pulse { 50% { opacity:.35; } }

      .list { display:flex; flex-direction:column; gap:6px; }
      .row { display:grid; grid-template-columns:24px 1fr auto; align-items:center; gap:10px;
             padding:9px 12px; border-radius:12px; background:var(--esg-row); transition:background .3s; }
      .row ha-icon { --mdc-icon-size:20px; color:var(--esg-muted); }
      .row .name { font-weight:500; }
      .row .time { font-variant-numeric:tabular-nums; font-weight:600; }
      .row.minor { padding-top:6px; padding-bottom:6px; font-size:.88rem; }
      .row.minor .name, .row.minor .time { font-weight:400; color:var(--esg-muted); }
      .row.past { opacity:.55; }
      .row.active { background:var(--esg-row-active); box-shadow:inset 3px 0 0 var(--esg-accent); }
      .row.active ha-icon, .row.active .time { color:var(--esg-accent); }
      .row.upcoming .name::after { content:"•"; margin-left:6px; color:var(--esg-accent); }

      .notice { display:flex; align-items:center; gap:10px; padding:14px; border-radius:12px; background:var(--esg-row); }

      /* Compact: horizontal strip of prayers under a slim hero */
      .layout-compact .ring-wrap { width:120px; height:120px; }
      .layout-compact .cd { font-size:1.4rem; }
      .layout-compact .nname { font-size:.95rem; }
      .layout-compact .clock { font-size:3.0rem; }
      .layout-compact .lbl { font-size:.62rem; letter-spacing:1px; }
      .layout-compact .list { flex-direction:row; gap:4px; }
      .layout-compact .row { flex:1; grid-template-columns:1fr; text-align:center; justify-items:center; gap:2px; padding:8px 4px; font-size:.82rem; }
      .layout-compact .row.minor { padding:8px 4px; }
      .layout-compact .row.active { box-shadow:inset 0 -3px 0 var(--esg-accent); }
      .layout-compact .row.upcoming .name::after { content:""; }

      /* Wide (tablet/TV): ring + list side by side */
      @container (min-width: 680px) {
        .layout-auto .content, .layout-full .content { display:grid; grid-template-columns: auto 1fr; grid-template-rows:auto 1fr; column-gap:28px; }
        .layout-auto .header, .layout-full .header { grid-column:1 / -1; }
        .layout-auto .hero, .layout-full .hero { flex-direction:column; align-items:flex-start; }
        .layout-auto .ring-wrap, .layout-full .ring-wrap { width:220px; height:220px; }
        .layout-auto .cd, .layout-full .cd { font-size:2.4rem; }
        .layout-auto .clock, .layout-full .clock { font-size:4.4rem; }
        .layout-auto .list, .layout-full .list { justify-content:center; }
        .layout-auto .row, .layout-full .row { padding:12px 16px; font-size:1.1rem; }
      }
      @container (max-width: 380px) {
        .layout-auto .hero, .layout-full .hero { flex-direction:column; align-items:stretch; text-align:center; gap:12px; }
        .layout-auto .ring-wrap, .layout-full .ring-wrap { margin:0 auto; }
        .layout-auto .side, .layout-full .side { align-items:center; }
        .layout-auto .current-pill, .layout-full .current-pill { align-self:center; }
      }
      /* Compact keeps its desktop shape on phones: ring beside clock, one strip of prayers */
      @container (max-width: 460px) {
        .layout-compact .content { padding:14px 12px 12px; gap:12px; }
        .layout-compact .hero { gap:12px; }
        .layout-compact .ring-wrap { width:100px; height:100px; }
        .layout-compact .moon { inset:16px; width:calc(100% - 32px); height:calc(100% - 32px); }
        .layout-compact .cd { font-size:1.15rem; }
        .layout-compact .nname { font-size:.8rem; }
        .layout-compact .ntime { font-size:.7rem; }
        .layout-compact .lbl { font-size:.55rem; }
        .layout-compact .clock { font-size:2.3rem; }
        .layout-compact .clock .sec { font-size:.95rem; }
        .layout-compact .clock .ap { font-size:.9rem; margin-left:4px; }
        .layout-compact .dates { font-size:.74rem; }
        .layout-compact .current-pill { font-size:.7rem; padding:4px 9px; }
        .layout-compact .side { gap:6px; }
        .layout-compact .list { gap:3px; }
        .layout-compact .row, .layout-compact .row.minor { padding:7px 1px; font-size:.66rem; border-radius:9px; min-width:0; }
        .layout-compact .row ha-icon { --mdc-icon-size:16px; }
        .layout-compact .row .name, .layout-compact .row .time { white-space:nowrap; overflow:hidden; text-overflow:clip; max-width:100%; letter-spacing:-.2px; }
      }
      @container (max-width: 340px) {
        .layout-compact .ring-wrap { width:86px; height:86px; }
        .layout-compact .cd { font-size:1rem; }
        .layout-compact .clock { font-size:1.95rem; }
        .layout-compact .row, .layout-compact .row.minor { font-size:.6rem; }
      }
    `;
  }
}

if (!customElements.get("esolatgps-card")) {
customElements.define("esolatgps-card", EsolatGpsCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "esolatgps-card",
  name: "eSolat GPS Card",
  description: "Malaysia prayer times from eSolat GPS, with a live countdown, Hijri date and sky themes.",
  preview: true,
  documentationURL: "https://github.com/zubir2k/homeassistant-esolatgps",
});
}

console.info(
  `%c ESOLATGPS-CARD %c v${CARD_VERSION} `,
  "color:#fff;background:#0f3d2e;font-weight:700;padding:2px 4px;border-radius:3px 0 0 3px",
  "color:#0f3d2e;background:#d4af37;font-weight:700;padding:2px 4px;border-radius:0 3px 3px 0"
);
