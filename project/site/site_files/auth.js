/**
 * === AUTH.JS — Модуль авторизации для PC Builder ===
 * Версия: 3.2 (Исправлена работа с Cookies)
 */

// === 🔥 ГЛОБАЛЬНЫЕ КОНСТАНТЫ ===
if (typeof window.API_BASE === 'undefined') {
    window.API_BASE = (window.location.hostname === 'localhost' || 
                      window.location.hostname === '127.0.0.1' ||
                      window.location.protocol === 'file:')
        ? 'http://127.0.0.1:10000'
        : 'https://forgepower.рит.online';
    console.log('🔧 API_BASE:', window.API_BASE);
}

window.TOKEN_KEY = 'pcbuilder_auth';
window.USERNAME_KEY = 'pcbuilder_username';

// === НАСТРОЙКИ РОЛЕЙ ===
window.ROLES_CONFIG = {
    1: { name: 'Пользователь', color: '#00d4aa' },
    2: { name: 'Сборщик', color: '#00ff00' },
    3: { name: 'Администратор', color: '#ff6b6b' },
    4: { name: 'Разработчик', color: '#ffd93d' }
};

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

// === 🔥 МАППИНГ ПОЛЕЙ: БД → ФРОНТЕНД ===
function mapUserFields(dbUser) {
    if (!dbUser) return null;
    return {
        user_name: dbUser.user_name || dbUser.username || dbUser.sub || '',
        username: dbUser.user_name || dbUser.username || dbUser.sub || '',
        nickname: dbUser.nickname || dbUser.user_name || dbUser.username || '',
        user_email: dbUser.user_email || dbUser.email || '',
        email: dbUser.user_email || dbUser.email || '',
        user_img: dbUser.user_img || dbUser.avatar_url || dbUser.avatar || '',
        avatar_url: dbUser.user_img || dbUser.avatar_url || dbUser.avatar || '',
        avatar: dbUser.user_img || dbUser.avatar_url || dbUser.avatar || '',
        role: typeof dbUser.role === 'number' ? dbUser.role : 
              typeof dbUser.role === 'string' ? parseInt(dbUser.role) : 1,
        _id: dbUser._id || dbUser.id || '',
        id: dbUser._id || dbUser.id || '',
        user_phone: dbUser.user_phone || dbUser.phone || '',
        created_at: dbUser.created_at || null,
        updated_at: dbUser.updated_at || null
    };
}

// === АВТОРИЗАЦИЯ И ТОКЕНЫ ===
function isAuthenticated() {
    return !!getCookie(window.TOKEN_KEY) && !!getCookie(window.USERNAME_KEY);
}

function getCurrentUsername() {
    return getCookie(window.USERNAME_KEY);
}

function getToken() {
    return getCookie(window.TOKEN_KEY) || '';
}

// === ПОЛУЧЕНИЕ ПРОФИЛЯ ===
async function fetchProfile(username) {
    const token = getToken();
    
    if (!token) {
        console.warn('⚠️ Токен не найден');
        return null;
    }
    
    try {
        const response = await fetch(`${API_BASE}/users/${username}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                deleteCookie(window.TOKEN_KEY);
                deleteCookie(window.USERNAME_KEY);
            }
            return null;
        }
        
        const profile = await response.json();
        console.log('✅ Профиль загружен:', profile);
        return profile;
        
    } catch (error) {
        console.error('❌ Ошибка загрузки профиля:', error);
        return null;
    }
}

// === АВТАР ===
function buildAvatarUrl(pathFromDb) {
    if (!pathFromDb) return null;
    
    if (pathFromDb.startsWith('http://') || pathFromDb.startsWith('https://')) {
        const separator = pathFromDb.includes('?') ? '&' : '?';
        return `${pathFromDb}${separator}_cb=${Date.now()}`;
    }
    
    const separator = pathFromDb.includes('?') ? '&' : '?';
    return `http://127.0.0.1:10000${pathFromDb}${separator}_cb=${Date.now()}`;
}

function renderAvatarElement(profile, username, size = 36) {
    const displayName = profile?.nickname || profile?.user_name || username || 'U';
    const roleId = profile?.role || 1;
    const roleConfig = window.ROLES_CONFIG[roleId] || window.ROLES_CONFIG[1];
    
    const pathFromDb = profile?.avatar_url || profile?.user_img;
    const avatarUrl = buildAvatarUrl(pathFromDb);
    
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

function renderUserSection(containerId, profile = null) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.warn('⚠️ Контейнер userSection не найден');
        return;
    }

    if (!isAuthenticated()) {
        container.innerHTML = `
            <div class="auth-buttons-mini">
                <a href="login.html">Войти</a>
                <a href="register.html">Регистрация</a>
            </div>
        `;
        return;
    }

    const username = getCurrentUsername();
    const user = profile ? mapUserFields(profile) : null;
    const displayName = user?.nickname || user?.user_name || username || 'Пользователь';
    const roleId = user?.role || 1;
    const roleConfig = window.ROLES_CONFIG[roleId] || window.ROLES_CONFIG[1];
    
    container.innerHTML = `
        ${renderAvatarElement(user, username, 36)}
        <span style="color:${roleConfig.color};font-weight:700;font-size:15px;cursor:pointer;margin:0 8px" onclick="location.href='profile.html'">${displayName}</span>
        <span style="padding:4px 10px;border-radius:12px;font-size:11px;font-weight:700;background:${roleConfig.color}15;color:${roleConfig.color};border:1px solid ${roleConfig.color};white-space:nowrap">${roleConfig.name}</span>
        <button onclick="logout(event)" style="margin-left:10px;padding:6px 12px;background:#ff6b6b;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:12px">Выйти</button>
    `;
}

// === ЗАГРУЗКА/СБРОС АВАТАРА ===
async function uploadAvatar(fileInput) {
    const file = fileInput.files[0];
    if (!file) {
        alert('Выберите файл!');
        return;
    }
    
    const username = getCurrentUsername();
    const token = getToken();
    
    const formData = new FormData();
    formData.append('file', file);
    
    console.log('📤 Загрузка аватара:', file.name);
    
    try {
        const response = await fetch(`${API_BASE}/data/profile/${username}/avatar`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.detail || 'Ошибка загрузки');
        }
        
        alert('✅ Аватар загружен!');
        location.reload();
        
    } catch (error) {
        console.error('❌ Ошибка:', error);
        alert('Ошибка: ' + error.message);
    }
}

async function resetAvatar() {
    const username = getCurrentUsername();
    const token = getToken();
    
    if (!confirm('Сбросить аватар на стандартный?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/data/profile/${username}/avatar/reset`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.detail || 'Ошибка сброса');
        }
        
        alert('✅ Аватар сброшен!');
        location.reload();
        
    } catch (error) {
        console.error('❌ Ошибка:', error);
        alert('Ошибка: ' + error.message);
    }
}

// === ВЫХОД И ПЕРЕАДРЕСАЦИЯ ===
function logout(event) {
    if (event) event.preventDefault();
    deleteCookie(window.TOKEN_KEY);
    deleteCookie(window.USERNAME_KEY);
    window.location.href = 'index.html';
}

function requireAuth(redirect = 'login.html') {
    if (!isAuthenticated()) {
        const returnTo = encodeURIComponent(location.pathname + location.search);
        location.href = `${redirect}?return=${returnTo}`;
        return false;
    }
    return true;
}

// === ЭКСПОРТ ФУНКЦИЙ ===
if (typeof window !== 'undefined') {
    window.isAuthenticated = isAuthenticated;
    window.getCurrentUsername = getCurrentUsername;
    window.getToken = getToken;
    window.fetchProfile = fetchProfile;
    window.renderUserSection = renderUserSection;
    window.renderAvatarElement = renderAvatarElement;
    window.buildAvatarUrl = buildAvatarUrl;
    window.mapUserFields = mapUserFields;
    window.logout = logout;
    window.requireAuth = requireAuth;
    window.uploadAvatar = uploadAvatar;
    window.resetAvatar = resetAvatar;
    window.setCookie = setCookie;
    window.getCookie = getCookie;
    window.deleteCookie = deleteCookie;
}

console.log('✅ auth.js v3.2 loaded');