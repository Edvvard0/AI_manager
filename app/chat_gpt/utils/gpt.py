import asyncio

from app.chat_gpt.utils.utils import client
from app.config import settings


async def create_response_gpt(text: str):

    response = await client.responses.create(
        model=settings.CHAT_GPT_MODEL,
        input=text,
    )
    # print(response.output_text)
    return response.output_text

print(asyncio.run(create_response_gpt(text='''
это мой шаблон base.html вот эндпоинт который его загружает 

@router.get("/", response_class=HTMLResponse)
async def main_page(request: Request, chats = Depends(get_all_chats)):
    return templates.TemplateResponse("pages/main_page.html", {
        "request": request,
        "chats": chats
    })
    
сейчас данные о чатах подгружаются с помощью запроса на сервер от этого нужно уйти, все информацию о чатах, я уже передал в шаблон
но эта информация о всех чатах а мне ты должен отобразить только те кооторые chat.user_id == моему телеграмм id 
тулугамм id можно получить так  const userId = localStorage.getItem("userId");

пришли мне полностью переработаный шаблон

<!DOCTYPE html>
<html lang="ru">
<head>
    <title>{% block title %}{% endblock %}</title>
    <link href="/static/style/main.css?v=1.0.1" rel="stylesheet" type="text/css">
    <link href="/static/style/my_style.css?v=1.0.5" rel="stylesheet" type="text/css">
    <link rel="shortcut icon" href="/static/favicon.ico">
    <link rel="apple-touch-icon" href="/static/meta/apple-touch-icon.png">
    <link rel="apple-touch-startup-image" href="/static/meta/apple-touch-startup-image-640x1096.png"
          media="(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)">
    <link rel="apple-touch-startup-image" href="/static/meta/apple-touch-startup-image-640x920.png"
          media="(device-width: 320px) and (device-height: 480px) and (-webkit-device-pixel-ratio: 2)">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="/static/js/tg_config.js?v=1.0.2"></script>
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
    <meta name="HandheldFriendly" content="True">
    <meta name="MobileOptimized" content="320">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, minimal-ui">
<style>
    body {
        margin: 0;
        padding: 0;
        background-color: #ffffff;
        color: #000000;
        font-family: Arial, sans-serif;
        display: flex;
        height: 100vh;
        overflow: hidden;
    }

    .header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        display: flex;
        justify-content: flex-start;
        padding: 10px;
        background-color: #ffffff; /* убрали тёмную заливку */
        z-index: 10;
        border-bottom: none; /* убрали линию */
    }

    .menu-button {
        font-size: 24px;
        color: #000000;
        cursor: pointer;
        touch-action: manipulation;
    }

    .sidebar {
        position: fixed;
        top: 0;
        left: -300px;
        width: 300px;
        height: 100%;
        background-color: #ffffff;
        transition: left 0.3s ease;
        padding: 20px 0;
        z-index: 20;
        color: #000000;
        overflow-y: auto;
        box-shadow: 2px 0 5px rgba(0,0,0,0.1);
    }

    .sidebar.open {
        left: 0;
    }

    .close-button {
        position: absolute;
        top: 10px;
        right: 10px;
        font-size: 24px;
        color: #000000;
        cursor: pointer;
        touch-action: manipulation;
    }

    .chat-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .chat-item {
        padding: 15px 20px;
        cursor: pointer;
        border-bottom: 1px solid #e0e0e0;
        font-size: 16px;
    }

    .chat-item:hover {
        background-color: #f0f0f0;
    }

    .new-chat-button,
    .token-button {
        padding: 10px 20px;
        background-color: #ffffff;
        color: #000000;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        width: 90%;
        margin: 10px auto;
        display: block;
        font-size: 14px;
        touch-action: manipulation;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        transition: background-color 0.2s;
    }

    .new-chat-button:hover,
    .token-button:hover {
        background-color: #f0f0f0;
    }

    .modal {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.1);
        justify-content: center;
        align-items: center;
        z-index: 30;
    }

    .modal-content {
        background-color: #ffffff;
        padding: 15px 15px 20px 15px; /* убрали обводку, сократили паддинги сверху */
        border-radius: 5px;
        text-align: center;
        width: 300px;
        box-sizing: border-box;
        max-width: 90%;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }

    #chat-name-input {
        width: calc(100% - 20px);
        padding: 10px;
        margin-bottom: 8px; /* уменьшили расстояние до кнопки */
        border: 1px solid #ccc;
        border-radius: 5px;
        box-sizing: border-box;
        outline: none;
    }

    #create-chat-button {
        padding: 10px 20px;
        background-color: #ffffff;
        color: #000000;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        width: calc(100% - 20px);
        touch-action: manipulation;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        transition: background-color 0.2s;
    }

    #create-chat-button:hover {
        background-color: #f0f0f0;
    }
</style>

    {% block extra_head %}{% endblock %}
</head>
<body>
    <div class="header">
        <div class="menu-button" id="menu-button">☰</div>
    </div>
    <div class="sidebar" id="sidebar">
        <div class="close-button" id="close-button">×</div>
        <h3 style="margin-left: 20px;">Чаты</h3>
        <ul class="chat-list" id="chat-list">
            <!-- Чаты будут добавлены динамически -->
        </ul>
        <button class="new-chat-button" id="new-chat-button">Создать новый чат</button>
        <button class="token-button" id="token-button">Токены</button>
    </div>
    <div class="modal" id="new-chat-modal">
        <div class="modal-content">
            <input type="text" id="chat-name-input" placeholder="Введите название чата...">
            <button id="create-chat-button">Создать</button>
        </div>
    </div>
    {% block content %}{% endblock %}
    {% block extra_scripts %}{% endblock %}
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            // Проверка инициализации Telegram Web App
            if (typeof window.Telegram === 'undefined' || !window.Telegram.WebApp) {
                console.error('Telegram WebApp is not loaded. Ensure telegram-web-app.js is loaded correctly.');
                alert('Ошибка: Telegram WebApp не загружен');
                return;
            }

            // Инициализация Telegram Web App
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();

            const sidebar = document.getElementById('sidebar');
            const menuButton = document.getElementById('menu-button');
            const closeButton = document.getElementById('close-button');
            const newChatButton = document.getElementById('new-chat-button');
            const newChatModal = document.getElementById('new-chat-modal');
            const createChatButton = document.getElementById('create-chat-button');
            const chatList = document.getElementById('chat-list');
            const tokenButton = document.getElementById('token-button');

            // Проверка наличия элементов DOM
            if (!menuButton || !sidebar || !closeButton || !newChatButton || !newChatModal || !createChatButton || !chatList || !tokenButton) {
                console.error('One or more DOM elements not found:', {
                    menuButton, sidebar, closeButton, newChatButton, newChatModal, createChatButton, chatList, tokenButton
                });
                alert('Ошибка: один или несколько элементов DOM не найдены');
                return;
            }

            // Открытие бокового меню
            menuButton.addEventListener('click', () => {
                console.log('Menu button clicked');
                sidebar.classList.add('open');
                const userId = window.Telegram.WebApp.initDataUnsafe?.user?.id || localStorage.getItem('userId');
                if (userId) {
                    console.log('Fetching chats for userId:', userId);
                    fetchChats(userId);
                } else {
                    console.error('User ID not found. Ensure Telegram WebApp is initialized or userId is stored in localStorage.');
                    alert('Ошибка: пользователь не идентифицирован');
                }
            });

            // Закрытие бокового меню
            closeButton.addEventListener('click', () => {
                sidebar.classList.remove('open');
            });

            // Открытие модального окна для создания чата
            newChatButton.addEventListener('click', () => {
                console.log('New chat button clicked');
                newChatModal.style.display = 'flex';
            });

            // Обработка создания чата
            const handleCreateChat = async () => {
                const chatName = document.getElementById('chat-name-input').value.trim();
                const userId = window.Telegram.WebApp.initDataUnsafe?.user?.id || localStorage.getItem('userId');
                if (!chatName) {
                    console.error('Chat name is empty');
                    alert('Пожалуйста, введите название чата');
                    return;
                }
                if (!userId) {
                    console.error('User ID is missing');
                    alert('Ошибка: пользователь не идентифицирован');
                    return;
                }

                console.log('Creating chat with name:', chatName, 'for userId:', userId);
                try {
                    const response = await fetch(`/chat_gpt/chats/?tg_id=${userId}&title=${encodeURIComponent(chatName)}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        }
                    });
                    const contentType = response.headers.get('content-type');
                    const text = await response.text();
                    console.log('Raw response from POST /chat_gpt/chats:', text, 'Content-Type:', contentType, 'Status:', response.status);
                    if (!contentType || !contentType.includes('application/json')) {
                        console.error('Non-JSON response received from POST /chat_gpt/chats:', text);
                        alert(`Ошибка в POST /chat_gpt/chats:\nСервер вернул не-JSON ответ\nURL: ${response.url}\nContent-Type: ${contentType || 'не указан'}\nStatus: ${response.status}\nResponse: ${text.substring(0, 200)}${text.length > 200 ? '...' : ''}`);
                        throw new Error('Server returned non-JSON response');
                    }
                    let data;
                    try {
                        data = JSON.parse(text);
                    } catch (e) {
                        console.error('Failed to parse POST response as JSON:', text);
                        alert(`Ошибка в POST /chat_gpt/chats:\nНе удалось разобрать JSON\nURL: ${response.url}\nContent-Type: ${contentType}\nStatus: ${response.status}\nResponse: ${text.substring(0, 200)}${text.length > 200 ? '...' : ''}`);
                        throw new Error(`Failed to parse JSON: ${text}`);
                    }
                    if (!response.ok) {
                        console.error('POST /chat_gpt/chats failed:', response.status, data);
                        alert(`Ошибка в POST /chat_gpt/chats:\nСтатус: ${response.status}\nURL: ${response.url}\nResponse: ${JSON.stringify(data)}`);
                        throw new Error(`Network response was not ok: ${response.status}, ${JSON.stringify(data)}`);
                    }
                    console.log('Chat created:', data);
                    await fetchChats(userId);
                    newChatModal.style.display = 'none';
                    document.getElementById('chat-name-input').value = '';
                } catch (error) {
                    console.error('Error creating chat:', error);
                    alert(`Ошибка при создании чата:\n${error.message}\nURL: ${response?.url || 'не определён'}`);
                }
            };

            // Обработчики для click и touchend
            createChatButton.addEventListener('click', handleCreateChat);
            createChatButton.addEventListener('touchend', (e) => {
                e.preventDefault();
                console.log('Create chat button touched');
                handleCreateChat();
            });

            // Закрытие модального окна при клике вне области
            newChatModal.addEventListener('click', (e) => {
                if (e.target === newChatModal) {
                    newChatModal.style.display = 'none';
                    document.getElementById('chat-name-input').value = '';
                }
            });

            // Навигация по кнопке "Токены"
            tokenButton.addEventListener('click', () => {
                console.log('Token button clicked');
                window.location.href = '/pages/token_info';
            });

            // Получение списка чатов
            async function fetchChats(userId) {
                let chatList = document.getElementById('chat-list');
                if (!chatList) {
                    console.warn('Element with id "chat-list" not found, creating it...');
                    chatList = document.createElement('ul');
                    chatList.id = 'chat-list';
                    chatList.classList.add('chat-list');
                    const sidebar = document.getElementById('sidebar');
                    if (sidebar) {
                        sidebar.insertBefore(chatList, sidebar.querySelector('.new-chat-button'));
                    } else {
                        document.body.appendChild(chatList);
                    }
                }

                try {
                    const response = await fetch(`/chat_gpt/chats/${userId}`, {
                        headers: {
                            'Accept': 'application/json'
                        }
                    });

                    const contentType = response.headers.get('content-type');
                    if (!contentType || !contentType.includes('application/json')) {
                        const text = await response.text();
                        console.error('Non-JSON response received from GET /chat_gpt/chats:', text);
                        alert(`Ошибка в GET /chat_gpt/chats:\nСервер вернул не-JSON ответ\nURL: ${response.url}\nContent-Type: ${contentType || 'не указан'}\nStatus: ${response.status}\nResponse: ${text.substring(0, 200)}${text.length > 200 ? '...' : ''}`);
                        throw new Error('Server returned non-JSON response');
                    }

                    const chats = await response.json();
                    if (!response.ok) {
                        console.error('GET /chat_gpt/chats failed:', response.status, chats);
                        alert(`Ошибка в GET /chat_gpt/chats:\nСтатус: ${response.status}\nURL: ${response.url}\nResponse: ${JSON.stringify(chats)}`);
                        throw new Error(`HTTP error! status: ${response.status}, ${JSON.stringify(chats)}`);
                    }

                    console.log('Received chats from server:', chats);
                    chatList.innerHTML = '';
                    if (Array.isArray(chats)) {
                        chats.forEach(chat => {
                            const chatItem = document.createElement('li');
                            chatItem.classList.add('chat-item');
                            chatItem.textContent = chat.title || 'Без названия';
                            chatItem.dataset.chatId = chat.id;
                            chatItem.addEventListener('click', () => {
                                console.log('Navigating to chat:', chat.id);
                                window.location.href = `/pages/current_chat/${chat.id}`;
                            });
                            chatList.appendChild(chatItem);
                        });
                    } else {
                        console.warn('Expected an array of chats, but got:', chats);
                        alert('Ошибка: Сервер вернул некорректные данные чатов');
                    }
                } catch (error) {
                    console.error('Ошибка при загрузке чатов:', error);
                    alert(`Ошибка при загрузке чатов:\n${error.message}\nURL: ${error.response?.url || 'не определён'}`);
                }
            }
        });
    </script>
</html>

эта ошибка которую я получаю

    raise TypeError(f'Object of type {o.__class__.__name__} '
                    f'is not JSON serializable')
TypeError: Object of type Chat is not JSON serializable

вот шаблон который ты прислал

<!DOCTYPE html>
<html lang="ru">
<head>
    <title>{% block title %}{% endblock %}</title>
    <link href="/static/style/main.css?v=1.0.1" rel="stylesheet" type="text/css">
    <link href="/static/style/my_style.css?v=1.0.5" rel="stylesheet" type="text/css">
    <link rel="shortcut icon" href="/static/favicon.ico">
    <link rel="apple-touch-icon" href="/static/meta/apple-touch-icon.png">
    <link rel="apple-touch-startup-image" href="/static/meta/apple-touch-startup-image-640x1096.png"
          media="(device-width: 320px) and (device-height: 568px) and (-webkit-device-pixel-ratio: 2)">
    <link rel="apple-touch-startup-image" href="/static/meta/apple-touch-startup-image-640x920.png"
          media="(device-width: 320px) and (device-height: 480px) and (-webkit-device-pixel-ratio: 2)">
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="/static/js/tg_config.js?v=1.0.2"></script>
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
    <meta name="HandheldFriendly" content="True">
    <meta name="MobileOptimized" content="320">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, minimal-ui">
<style>
    body {
        margin: 0;
        padding: 0;
        background-color: #ffffff;
        color: #000000;
        font-family: Arial, sans-serif;
        display: flex;
        height: 100vh;
        overflow: hidden;
    }

    .header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        display: flex;
        justify-content: flex-start;
        padding: 10px;
        background-color: #ffffff;
        z-index: 10;
        border-bottom: none;
    }

    .menu-button {
        font-size: 24px;
        color: #000000;
        cursor: pointer;
        touch-action: manipulation;
    }

    .sidebar {
        position: fixed;
        top: 0;
        left: -300px;
        width: 300px;
        height: 100%;
        background-color: #ffffff;
        transition: left 0.3s ease;
        padding: 20px 0;
        z-index: 20;
        color: #000000;
        overflow-y: auto;
        box-shadow: 2px 0 5px rgba(0,0,0,0.1);
    }

    .sidebar.open {
        left: 0;
    }

    .close-button {
        position: absolute;
        top: 10px;
        right: 10px;
        font-size: 24px;
        color: #000000;
        cursor: pointer;
        touch-action: manipulation;
    }

    .chat-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .chat-item {
        padding: 15px 20px;
        cursor: pointer;
        border-bottom: 1px solid #e0e0e0;
        font-size: 16px;
    }

    .chat-item:hover {
        background-color: #f0f0f0;
    }

    .new-chat-button,
    .token-button {
        padding: 10px 20px;
        background-color: #ffffff;
        color: #000000;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        width: 90%;
        margin: 10px auto;
        display: block;
        font-size: 14px;
        touch-action: manipulation;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        transition: background-color 0.2s;
    }

    .new-chat-button:hover,
    .token-button:hover {
        background-color: #f0f0f0;
    }

    .modal {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.1);
        justify-content: center;
        align-items: center;
        z-index: 30;
    }

    .modal-content {
        background-color: #ffffff;
        padding: 15px 15px 20px 15px;
        border-radius: 5px;
        text-align: center;
        width: 300px;
        box-sizing: border-box;
        max-width: 90%;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }

    #chat-name-input {
        width: calc(100% - 20px);
        padding: 10px;
        margin-bottom: 8px;
        border: 1px solid #ccc;
        border-radius: 5px;
        box-sizing: border-box;
        outline: none;
    }

    #create-chat-button {
        padding: 10px 20px;
        background-color: #ffffff;
        color: #000000;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        width: calc(100% - 20px);
        touch-action: manipulation;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        transition: background-color 0.2s;
    }

    #create-chat-button:hover {
        background-color: #f0f0f0;
    }
</style>

    {% block extra_head %}{% endblock %}
</head>
<body>
    <div class="header">
        <div class="menu-button" id="menu-button">☰</div>
    </div>

    <div class="sidebar" id="sidebar">
        <div class="close-button" id="close-button">×</div>
        <h3 style="margin-left: 20px;">Чаты</h3>
        <ul class="chat-list" id="chat-list"></ul>
        <button class="new-chat-button" id="new-chat-button">Создать новый чат</button>
        <button class="token-button" id="token-button">Токены</button>
    </div>

    <div class="modal" id="new-chat-modal">
        <div class="modal-content">
            <input type="text" id="chat-name-input" placeholder="Введите название чата...">
            <button id="create-chat-button">Создать</button>
        </div>
    </div>

    {% block content %}{% endblock %}
    {% block extra_scripts %}{% endblock %}

    <!-- Встроенные данные о всех чатах, переданные из бекенда -->
    <script id="seed-chats" type="application/json">{{ chats | tojson | safe }}</script>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            // Инициализация Telegram WebApp (если доступен)
            const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
            if (tg) {
                try { tg.ready(); tg.expand(); } catch (_) {}
            }

            // DOM элементы
            const sidebar = document.getElementById('sidebar');
            const menuButton = document.getElementById('menu-button');
            const closeButton = document.getElementById('close-button');
            const newChatButton = document.getElementById('new-chat-button');
            const newChatModal = document.getElementById('new-chat-modal');
            const createChatButton = document.getElementById('create-chat-button');
            const chatListEl = document.getElementById('chat-list');
            const tokenButton = document.getElementById('token-button');

            // Чаты, переданные из шаблона
            let ALL_CHATS = [];
            (function loadSeedChats() {
                const seed = document.getElementById('seed-chats');
                if (seed) {
                    try {
                        ALL_CHATS = JSON.parse(seed.textContent || '[]') || [];
                    } catch (e) {
                        console.error('Не удалось разобрать seed-чаты из шаблона', e);
                        ALL_CHATS = [];
                    }
                }
                window.__ALL_CHATS__ = ALL_CHATS;
            })();

            // Получение текущего userId (сначала из localStorage, затем из Telegram WebApp)
            function getCurrentUserId() {
                const fromLS = localStorage.getItem('userId');
                if (fromLS) return fromLS;
                return tg?.initDataUnsafe?.user?.id ? String(tg.initDataUnsafe.user.id) : null;
            }

            // Рендер чатов по userId без запросов к серверу
            function renderChatsForUser(userId) {
                if (!chatListEl) return;
                chatListEl.innerHTML = '';
                if (!userId) {
                    const info = document.createElement('li');
                    info.className = 'chat-item';
                    info.textContent = 'Пользователь не идентифицирован';
                    chatListEl.appendChild(info);
                    return;
                }
                const list = (ALL_CHATS || []).filter(c => String(c.user_id) === String(userId));
                if (!list.length) {
                    const empty = document.createElement('li');
                    empty.className = 'chat-item';
                    empty.textContent = 'Чатов пока нет';
                    chatListEl.appendChild(empty);
                    return;
                }
                list.forEach(chat => {
                    const li = document.createElement('li');
                    li.className = 'chat-item';
                    li.textContent = chat.title || 'Без названия';
                    li.dataset.chatId = chat.id;
                    li.addEventListener('click', () => {
                        window.location.href = `/pages/current_chat/${chat.id}`;
                    });
                    chatListEl.appendChild(li);
                });
            }

            // Открыть меню и отрисовать чаты
            menuButton?.addEventListener('click', () => {
                sidebar?.classList.add('open');
                const userId = getCurrentUserId();
                renderChatsForUser(userId);
            });

            // Закрыть меню
            closeButton?.addEventListener('click', () => {
                sidebar?.classList.remove('open');
            });

            // Открыть модал создания
            newChatButton?.addEventListener('click', () => {
                newChatModal.style.display = 'flex';
                document.getElementById('chat-name-input')?.focus();
            });

            // Закрыть модал при клике мимо
            newChatModal?.addEventListener('click', (e) => {
                if (e.target === newChatModal) {
                    newChatModal.style.display = 'none';
                    const input = document.getElementById('chat-name-input');
                    if (input) input.value = '';
                }
            });

            // Навигация "Токены"
            tokenButton?.addEventListener('click', () => {
                window.location.href = '/pages/token_info';
            });

            // Создание чата (POST), обновляем локальный список без GET
            async function handleCreateChat() {
                const input = document.getElementById('chat-name-input');
                const chatName = input?.value?.trim();
                const userId = getCurrentUserId();

                if (!chatName) {
                    alert('Пожалуйста, введите название чата');
                    return;
                }
                if (!userId) {
                    alert('Ошибка: пользователь не идентифицирован');
                    return;
                }

                try {
                    const response = await fetch(`/chat_gpt/chats/?tg_id=${encodeURIComponent(userId)}&title=${encodeURIComponent(chatName)}`, {
                        method: 'POST',
                        headers: {
                            'Accept': 'application/json'
                        }
                    });

                    const text = await response.text();
                    const contentType = response.headers.get('content-type') || '';
                    if (!contentType.includes('application/json')) {
                        throw new Error(`Сервер вернул не-JSON ответ. Status: ${response.status}. Response: ${text.slice(0, 200)}`);
                    }
                    const data = JSON.parse(text);
                    if (!response.ok) {
                        throw new Error(`Ошибка ${response.status}: ${JSON.stringify(data)}`);
                    }

                    // Добавляем созданный чат в локальный кэш и перерисовываем
                    const created = Array.isArray(data) ? data[0] : data;
                    if (created) {
                        if (!created.user_id) {
                            created.user_id = isNaN(Number(userId)) ? userId : Number(userId);
                        }
                        ALL_CHATS.push(created);
                        renderChatsForUser(userId);
                    }

                    newChatModal.style.display = 'none';
                    if (input) input.value = '';
                } catch (err) {
                    console.error('Ошибка при создании чата:', err);
                    alert(`Ошибка при создании чата: ${err.message}`);
                }
            }

            createChatButton?.addEventListener('click', handleCreateChat);
            createChatButton?.addEventListener('touchend', (e) => {
                e.preventDefault();
                handleCreateChat();
            });
        });
    </script>
</html>
''')))