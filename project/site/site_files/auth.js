/**
 * === AUTH.JS — Модуль авторизации для PC Builder ===
 */

// === ГЛОБАЛЬНЫЕ КОНСТАНТЫ ===
if (typeof window.API_BASE === 'undefined') {
    window.API_BASE = 'http://127.0.0.1:10000';
}
if (typeof window.TOKEN_KEY === 'undefined') {
    window.TOKEN_KEY = 'pcbuilder_auth';
}
if (typeof window.USERNAME_KEY === 'undefined') {
    window.USERNAME_KEY = 'pcbuilder_username';
}

// === НАСТРОЙКИ РОЛЕЙ (ЦВЕТА) ===
// role_id: { название, цвет текста/границы }
window.ROLES_CONFIG = {
    1: { name: 'Пользователь', color: '#00d4aa' },      // Бирюзовый
    2: { name: 'Сборщик', color: '#00ff00' },           // Зеленый
    3: { name: 'Администратор', color: '#ff6b6b' },     // Красный
    4: { name: 'Разработчик', color: '#ffd93d' }        // Желтый
};

const API_BASE = window.API_BASE;
const TOKEN_KEY = window.TOKEN_KEY;
const USERNAME_KEY = window.USERNAME_KEY;
const ROLES_CONFIG = window.ROLES_CONFIG;

// === РАБОТА С КУКИ ===
function setCookie(name, value, days = 7) {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
}

function deleteCookie(name) {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

// === ПРОВЕРКА АВТОРИЗАЦИИ ===
function isAuthenticated() {
    return !!getCookie(TOKEN_KEY) && !!getCookie(USERNAME_KEY);
}

function getCurrentUsername() {
    return getCookie(USERNAME_KEY);
}

function getToken() {
    return getCookie(TOKEN_KEY);
}

// === ЗАГРУЗКА ПРОФИЛЯ ===
async function fetchProfile(username) {
    try {
        const token = getToken();
        if (!token) return null;
        
        const response = await fetch(`${API_BASE}/data/profile/${username}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (!response.ok) return null;
        return await response.json();
    } catch (e) {
        console.error('Ошибка загрузки профиля:', e);
        return null;
    }
}

// === ОТРИСОВКА ШАПКИ ===
function renderUserSection(containerId, profile = null) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!isAuthenticated()) {
        container.innerHTML = `
            <div class="auth-buttons-mini">
                <a href="login.html" class="btn-login-mini">Войти</a>
                <a href="register.html" class="btn-register-mini">Регистрация</a>
            </div>
        `;
        return;
    }

    const username = getCurrentUsername();
    const displayName = profile?.nickname || profile?.user_name || username;
    const roleId = profile?.role || 1;
    const roleConfig = ROLES_CONFIG[roleId] || ROLES_CONFIG[1];
    
    // 🔥 ПРАВИЛЬНОЕ ФОРМИРОВАНИЕ URL АВАТАРА
    let avatarHtml = '';
    const rawAvatarUrl = profile?.avatar_url || profile?.user_img;
    
    if (rawAvatarUrl) {
        // Если URL относительный (начинается с /) — добавляем API_BASE
        const fullUrl = rawAvatarUrl.startsWith('http') 
            ? rawAvatarUrl 
            : `${API_BASE}${rawAvatarUrl}`;
        
        avatarHtml = `
            <img src="${fullUrl}" alt="${displayName}" style="width:100%;height:100%;object-fit:cover" 
                 onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'">
            <div class="user-avatar-placeholder" style="display:none;width:100%;height:100%;background:${roleConfig.color};display:flex;align-items:center;justify-content:center;font-weight:bold;color:#1a1a2e;font-size:16px">
                ${displayName.charAt(0).toUpperCase()}
            </div>
        `;
    } else {
        avatarHtml = `
            <div class="user-avatar-placeholder" style="width:100%;height:100%;background:${roleConfig.color};display:flex;align-items:center;justify-content:center;font-weight:bold;color:#1a1a2e;font-size:16px">
                ${displayName.charAt(0).toUpperCase()}
            </div>
        `;
    }

    container.innerHTML = `
        <div class="user-avatar" onclick="location.href='profile.html'" title="Профиль" style="width:36px;height:36px;border-radius:50%;overflow:hidden;border:2px solid ${roleConfig.color};cursor:pointer;background:#2a2a3e;flex-shrink:0;">
            ${avatarHtml}
        </div>
        <span class="user-name" onclick="location.href='profile.html'" style="color:${roleConfig.color};font-weight:700;font-size:15px;cursor:pointer;margin:0 8px;text-shadow: 0 0 2px rgba(0,0,0,0.5);">
            ${displayName}
        </span>
        <span class="role-badge" style="padding:4px 10px;border-radius:12px;font-size:11px;font-weight:700;background:${roleConfig.color}15;color:${roleConfig.color};border:1px solid ${roleConfig.color};white-space:nowrap;">
            ${roleConfig.name}
        </span>
        <button onclick="logout(event)" style="margin-left:10px;padding:6px 12px;background:#ff6b6b;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px;">Выйти</button>
    `;
}

// === ВЫХОД ===
function logout(event) {
    if (event) event.preventDefault();
    deleteCookie(TOKEN_KEY);
    deleteCookie(USERNAME_KEY);
    location.href = 'index.html';
}

// === ПЕРЕАДРЕСАЦИЯ ===
function requireAuth(redirect = 'login.html') {
    if (!isAuthenticated()) {
        const returnTo = encodeURIComponent(location.pathname + location.search);
        location.href = `${redirect}?return=${returnTo}`;
        return false;
    }
    return true;
}

// === ФУНКЦИЯ ПОЛУЧЕНИЯ ПОЛНОГО URL АВАТАРА ===
function getAvatarUrl(rawUrl, username) {
    if (!rawUrl) {
        return null;
    }
    // Если уже полный URL — возвращаем как есть
    if (rawUrl.startsWith('http://') || rawUrl.startsWith('https://')) {
        return rawUrl;
    }
    // Если относительный путь — добавляем API_BASE
    return `${API_BASE}${rawUrl}`;
}

// === ФУНКЦИЯ ОТРИСОВКИ АВАТАРА ===
function renderAvatar(container, profile, username, size = 36) {
    const displayName = profile?.nickname || profile?.user_name || username || 'U';
    const roleId = profile?.role || 1;
    const roleConfig = ROLES_CONFIG[roleId] || ROLES_CONFIG[1];
    const rawAvatarUrl = profile?.avatar_url || profile?.user_img;
    const avatarUrl = getAvatarUrl(rawAvatarUrl, username);
    
    // HTML для аватара с обработкой ошибки загрузки
    const avatarHtml = avatarUrl 
        ? `<img src="${avatarUrl}" alt="${displayName}" 
               style="width:100%;height:100%;object-fit:cover"
               onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
           <div class="avatar-placeholder" style="display:none;align-items:center;justify-content:center;font-weight:bold;color:#1a1a2e;font-size:${Math.floor(size/2)}px;background:${roleConfig.color}">
               ${displayName.charAt(0).toUpperCase()}
           </div>`
        : `<div class="avatar-placeholder" style="display:flex;align-items:center;justify-content:center;font-weight:bold;color:#1a1a2e;font-size:${Math.floor(size/2)}px;background:${roleConfig.color}">
               ${displayName.charAt(0).toUpperCase()}
           </div>`;
    
    return `
        <div style="width:${size}px;height:${size}px;border-radius:50%;overflow:hidden;border:2px solid ${roleConfig.color};background:#2a2a3e;flex-shrink:0;cursor:pointer" 
             onclick="location.href='profile.html'">
            ${avatarHtml}
        </div>
    `;
}

// === ОБНОВЛЁННАЯ renderUserSection ===
function renderUserSection(containerId, profile = null) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!isAuthenticated()) {
        container.innerHTML = `
            <div class="auth-buttons-mini">
                <a href="login.html" class="btn-login-mini">Войти</a>
                <a href="register.html" class="btn-register-mini">Регистрация</a>
            </div>
        `;
        return;
    }

    const username = getCurrentUsername();
    const displayName = profile?.nickname || profile?.user_name || username;
    const roleId = profile?.role || 1;
    const roleConfig = ROLES_CONFIG[roleId] || ROLES_CONFIG[1];
    
    container.innerHTML = `
        ${renderAvatar(container, profile, username, 36)}
        <span style="color:${roleConfig.color};font-weight:700;font-size:15px;cursor:pointer;margin:0 8px" onclick="location.href='profile.html'">${displayName}</span>
        <span style="padding:4px 10px;border-radius:12px;font-size:11px;font-weight:700;background:${roleConfig.color}15;color:${roleConfig.color};border:1px solid ${roleConfig.color};white-space:nowrap">${roleConfig.name}</span>
        <button onclick="logout(event)" style="margin-left:10px;padding:6px 12px;background:#ff6b6b;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px">Выйти</button>
    `;
}
// === ФУНКЦИЯ: Путь из БД → Полный URL для браузера ===
function buildAvatarUrl(pathFromDb) {
    // Если путь пустой — возвращаем null
    if (!pathFromDb) return null;
    
    // Если уже полный URL (http/https) — возвращаем как есть
    if (pathFromDb.startsWith('http://') || pathFromDb.startsWith('https://')) {
        return pathFromDb;
    }
    
    // Если путь начинается с / — добавляем API_BASE
    if (pathFromDb.startsWith('/')) {
        return `${API_BASE}${pathFromDb}`;
    }
    
    // Если путь без ведущего / — добавляем / и API_BASE
    return `${API_BASE}/${pathFromDb}`;
}

// === ФУНКЦИЯ: Отрисовка аватара ===
function renderAvatarElement(profile, username, size = 36) {
    const displayName = profile?.nickname || profile?.user_name || username || 'U';
    const roleId = profile?.role || 1;
    const roleConfig = ROLES_CONFIG[roleId] || ROLES_CONFIG[1];
    
    // 🔥 Получаем путь из БД и строим полный URL
    const pathFromDb = profile?.avatar_url || profile?.user_img;
    const avatarUrl = buildAvatarUrl(pathFromDb);
    
    // HTML аватара с обработкой ошибки загрузки
    const avatarHtml = avatarUrl 
        ? `<img src="${avatarUrl}" alt="${displayName}" 
               style="width:100%;height:100%;object-fit:cover"
               onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
           <div class="avatar-fallback" style="display:none;width:100%;height:100%;background:${roleConfig.color};display:flex;align-items:center;justify-content:center;font-weight:bold;color:#1a1a2e;font-size:${Math.floor(size/2)}px">
               ${displayName.charAt(0).toUpperCase()}
           </div>`
        : `<div class="avatar-fallback" style="width:100%;height:100%;background:${roleConfig.color};display:flex;align-items:center;justify-content:center;font-weight:bold;color:#1a1a2e;font-size:${Math.floor(size/2)}px">
               ${displayName.charAt(0).toUpperCase()}
           </div>`;
    
    return `
        <div style="width:${size}px;height:${size}px;border-radius:50%;overflow:hidden;border:2px solid ${roleConfig.color};background:#2a2a3e;flex-shrink:0;cursor:pointer" 
             onclick="location.href='profile.html'" title="Профиль">
            ${avatarHtml}
        </div>
    `;
}

// === ОБНОВЛЁННАЯ renderUserSection ===
function renderUserSection(containerId, profile = null) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!isAuthenticated()) {
        container.innerHTML = `
            <div class="auth-buttons-mini">
                <a href="login.html" class="btn-login-mini">Войти</a>
                <a href="register.html" class="btn-register-mini">Регистрация</a>
            </div>
        `;
        return;
    }

    const username = getCurrentUsername();
    const displayName = profile?.nickname || profile?.user_name || username;
    const roleId = profile?.role || 1;
    const roleConfig = ROLES_CONFIG[roleId] || ROLES_CONFIG[1];
    
    container.innerHTML = `
        ${renderAvatarElement(profile, username, 36)}
        <span style="color:${roleConfig.color};font-weight:700;font-size:15px;cursor:pointer;margin:0 8px" onclick="location.href='profile.html'">${displayName}</span>
        <span style="padding:4px 10px;border-radius:12px;font-size:11px;font-weight:700;background:${roleConfig.color}15;color:${roleConfig.color};border:1px solid ${roleConfig.color};white-space:nowrap">${roleConfig.name}</span>
        <button onclick="logout(event)" style="margin-left:10px;padding:6px 12px;background:#ff6b6b;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px">Выйти</button>
    `;
}