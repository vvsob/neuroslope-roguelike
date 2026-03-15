import { createGameRenderer } from "./spireApp.js";

const STORAGE_TOKEN_KEY = "neuroslope_token";
const STORAGE_NAME_KEY = "neuroslope_name";

const root = document.getElementById("app");

const app = {
  screen: "boot",
  token: null,
  profile: null,
  characters: [],
  selectedCharacterId: null,
  error: null,
  loadingMessage: "",
  ws: null,
  lobbyId: null,
  gameRenderer: null,
};

const isBackendOrigin = ["8000", "8001"].includes(window.location.port);
const inferredApiBase = isBackendOrigin
  ? ""
  : `${window.location.protocol}//${window.location.hostname}:8000`;
const API_BASE = window.NEUROSLOPE_API
  ? String(window.NEUROSLOPE_API).replace(/\/$/, "")
  : inferredApiBase;

init();

async function init() {
  if (!root) {
    return;
  }

  const storedToken = window.localStorage.getItem(STORAGE_TOKEN_KEY);
  if (storedToken) {
    app.token = storedToken;
    await loadProfile();
    return;
  }

  app.screen = "auth";
  render();
}

function render() {
  if (!root) {
    return;
  }

  if (app.screen === "game") {
    if (!app.gameRenderer) {
      app.gameRenderer = createGameRenderer(root, {
        onAction: sendGameAction,
      });
    }
    return;
  }

  if (app.screen === "auth") {
    root.innerHTML = renderAuth();
    bindAuthEvents();
    return;
  }

  if (app.screen === "menu") {
    root.innerHTML = renderMenu();
    bindMenuEvents();
    return;
  }

  root.innerHTML = renderLoading();
}

function renderAuth() {
  const storedName = window.localStorage.getItem(STORAGE_NAME_KEY) ?? "";
  return `
    <section class="overlay-card screen-card auth-card">
      <div>
        <p class="eyebrow">Neuroslope</p>
        <h2>Регистрация пилота</h2>
        <p class="muted">Введи имя, чтобы получить токен доступа.</p>
      </div>
      ${renderError()}
      <form class="auth-form" data-action="register">
        <label class="input-field">
          <span class="muted">Позывной</span>
          <input name="name" type="text" placeholder="Warden" value="${escapeHtml(storedName)}" required />
        </label>
        <button class="button-primary" type="submit">Создать токен</button>
      </form>
    </section>
  `;
}

function renderMenu() {
  const characters = app.characters || [];
  const selectedId = app.selectedCharacterId;
  const canStart = Boolean(selectedId);

  return `
    <section class="overlay-card screen-card menu-card">
      <div class="menu-header">
        <div>
          <p class="eyebrow">Оператор</p>
          <h2>${escapeHtml(app.profile?.name ?? "Пилот")}</h2>
          <p class="muted">Выбери персонажа для нового забега.</p>
        </div>
        <button class="button-muted" data-action="logout">Сменить игрока</button>
      </div>

      ${renderError()}

      <div class="character-grid">
        ${characters
          .map((character) => {
            const isSelected = String(character.id) === String(selectedId);
            return `
              <button class="character-card ${isSelected ? "selected" : ""}" data-action="select-character" data-id="${character.id}">
                <p class="eyebrow">Персонаж</p>
                <h3>${escapeHtml(character.name)}</h3>
                <p class="muted">HP ${character.health}</p>
              </button>
            `;
          })
          .join("")}
      </div>

      <div class="menu-actions">
        <button class="button-primary" data-action="start-game" ${canStart ? "" : "disabled"}>Начать новый ран</button>
      </div>
    </section>
  `;
}

function renderLoading() {
  const message = app.loadingMessage || "Подготовка рана...";
  return `
    <div class="boot-card">
      <p class="eyebrow">Neuroslope</p>
      <h1>Загрузка</h1>
      <p class="muted">${escapeHtml(message)}</p>
    </div>
  `;
}

function renderError() {
  if (!app.error) {
    return "";
  }
  return `
    <div class="error-banner">
      <p>${escapeHtml(app.error)}</p>
    </div>
  `;
}

function bindAuthEvents() {
  const form = root.querySelector("form[data-action='register']");
  if (!form) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(form);
    const name = String(formData.get("name") || "").trim();

    if (!name) {
      app.error = "Введи позывной.";
      render();
      return;
    }

    app.error = null;
    app.loadingMessage = "Регистрация пилота...";
    app.screen = "boot";
    render();

    try {
      const response = await apiRequest("/auth/register", {
        method: "POST",
        body: { name },
        auth: false,
      });

      if (!response?.token) {
        throw new Error("Registration failed.");
      }

      app.token = response.token;
      window.localStorage.setItem(STORAGE_TOKEN_KEY, app.token);
      window.localStorage.setItem(STORAGE_NAME_KEY, name);
      await loadProfile();
    } catch (error) {
      app.error = errorMessage(error);
      app.screen = "auth";
      render();
    }
  });
}

function bindMenuEvents() {
  for (const button of root.querySelectorAll("[data-action]")) {
    button.addEventListener("click", async () => {
      const action = button.dataset.action;
      const id = button.dataset.id;

      if (action === "logout") {
        logout();
        return;
      }

      if (action === "select-character") {
        app.selectedCharacterId = id;
        render();
        return;
      }

      if (action === "start-game") {
        if (!app.selectedCharacterId) {
          app.error = "Выбери персонажа, чтобы начать.";
          render();
          return;
        }
        await startNewGame();
      }
    });
  }
}

async function loadProfile() {
  app.loadingMessage = "Синхронизация...";
  app.screen = "boot";
  render();

  try {
    const profile = await apiRequest("/lobby/me", { method: "GET" });
    app.profile = profile;
    app.characters = profile?.characters ?? [];
    app.selectedCharacterId = app.characters[0]?.id ?? null;
    app.error = null;
    app.screen = "menu";
    render();
  } catch (error) {
    logout(errorMessage(error));
  }
}

async function startNewGame() {
  app.error = null;
  app.loadingMessage = "Создание игры...";
  app.screen = "boot";
  render();

  try {
    const response = await apiRequest("/lobby/new-game", {
      method: "POST",
      body: { character_id: Number(app.selectedCharacterId) },
    });

    if (!response?.id) {
      throw new Error("Server did not return a lobby id.");
    }

    // Ask the LLM to generate this run's content before connecting.
    // On failure we fall back to static content gracefully.
    try {
      app.loadingMessage = "Оракул плетёт твою судьбу...";
      render();
      const genResult = await apiRequest(`/game/generate/${response.id}`, { method: "POST" });
      if (genResult?.theme) {
        app.loadingMessage = `${genResult.theme}...`;
        render();
      }
    } catch (genError) {
      // Non-fatal: static content will be used
      console.warn("LLM generation skipped:", genError?.message);
      app.loadingMessage = "Подключение к башне...";
      render();
    }

    connectToGame(response.id);
  } catch (error) {
    app.error = errorMessage(error);
    app.screen = "menu";
    render();
  }
}

function connectToGame(lobbyId) {
  cleanupSocket();

  const token = app.token;
  if (!token) {
    logout("Missing token. Please register again.");
    return;
  }

  app.loadingMessage = "Connecting to spire...";
  app.screen = "boot";
  render();

  const url = `${buildWsBase()}/game/ws/${lobbyId}?token=${encodeURIComponent(token)}`;
  const ws = new WebSocket(url);
  app.ws = ws;
  app.lobbyId = lobbyId;

  ws.addEventListener("message", (event) => {
    const data = safeJson(event.data);
    if (!data) {
      return;
    }

    if (data.type === "state") {
      if (app.screen !== "game") {
        app.screen = "game";
        render();
      }
      app.gameRenderer?.setState(data.state, {
        fx: data.fx ?? [],
        sfx: data.sfx ?? [],
      });
      return;
    }

    if (data.type === "error") {
      app.error = data.message || "Ошибка сервера.";
    }
  });

  ws.addEventListener("close", () => {
    const wasInGame = app.screen === "game";
    cleanupSocket();
    app.error = wasInGame
      ? "Соединение потеряно. Вернись в меню и начни заново."
      : "Не удалось подключиться к серверу.";
    app.screen = "menu";
    render();
  });

  ws.addEventListener("error", () => {
    if (app.screen !== "game") {
      app.error = "Не удалось подключиться к серверу.";
      app.screen = "menu";
      render();
    }
  });
}

function sendGameAction(action, id) {
  if (!app.ws || app.ws.readyState !== WebSocket.OPEN) {
    return;
  }

  app.ws.send(JSON.stringify({
    type: "action",
    action,
    id,
  }));
}

function apiRequest(path, { method = "GET", body, auth = true } = {}) {
  const headers = {
    "Content-Type": "application/json",
  };

  if (auth && app.token) {
    headers.Authorization = `Bearer ${app.token}`;
  }

  return fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  }).then(async (response) => {
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : null;
    if (!response.ok) {
      const message = data?.detail || data?.error || response.statusText || "Request failed";
      throw new Error(message);
    }
    return data;
  });
}

function buildWsBase() {
  const origin = API_BASE || window.location.origin;
  if (origin.startsWith("https")) {
    return origin.replace("https", "wss");
  }
  if (origin.startsWith("http")) {
    return origin.replace("http", "ws");
  }
  return window.location.origin.replace("http", "ws");
}

function cleanupSocket() {
  if (app.ws) {
    app.ws.close();
  }
  app.ws = null;
  app.lobbyId = null;
  app.gameRenderer = null;
}

function logout(message) {
  cleanupSocket();
  app.token = null;
  app.profile = null;
  app.characters = [];
  app.selectedCharacterId = null;
  app.error = message || null;
  window.localStorage.removeItem(STORAGE_TOKEN_KEY);
  app.screen = "auth";
  render();
}

function safeJson(value) {
  try {
    return JSON.parse(value);
  } catch (error) {
    return null;
  }
}

function errorMessage(error) {
  if (error instanceof Error) {
    return error.message || "Unexpected error.";
  }
  return "Unexpected error.";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
