const chatHistory = document.getElementById('chat-history');
const queryInput = document.getElementById('query-input');
const sendBtn = document.getElementById('send-btn');

function formatContent(content) {
    const lines = content.split('\n');
    let inTable = false;
    let tableHtml = '';
    let processedHtml = [];

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (line.startsWith('|') && line.endsWith('|')) {
            if (!inTable) {
                inTable = true;
                tableHtml = '<div class="table-container"><table class="f1-table">';
            }

            const cells = line.split('|').slice(1, -1).map(c => c.trim());
            const isSeparator = cells.every(c => c.match(/^:-*-?:*$/) || c.match(/^-+$/));
            if (isSeparator) {
                continue;
            }

            const isHeader = !tableHtml.includes('</thead>');
            if (isHeader) {
                tableHtml += '<thead><tr>';
                cells.forEach(c => {
                    tableHtml += `<th>${c}</th>`;
                });
                tableHtml += '</tr></thead><tbody>';
            } else {
                tableHtml += '<tr>';
                cells.forEach(c => {
                    tableHtml += `<td>${c}</td>`;
                });
                tableHtml += '</tr>';
            }
        } else {
            if (inTable) {
                inTable = false;
                tableHtml += '</tbody></table></div>';
                processedHtml.push(tableHtml);
            }
            if (line !== '') {
                if (line.startsWith('####')) {
                    processedHtml.push(`<h4>${line.replace(/^####\s*/, '').trim()}</h4>`);
                } else if (line.startsWith('###')) {
                    processedHtml.push(`<h3>${line.replace(/^###\s*/, '').trim()}</h3>`);
                } else if (line.startsWith('<')) {
                    processedHtml.push(line);
                } else {
                    processedHtml.push(`<p>${line}</p>`);
                }
            }
        }
    }

    if (inTable) {
        tableHtml += '</tbody></table></div>';
        processedHtml.push(tableHtml);
    }

    let finalHtml = processedHtml.join('');
    finalHtml = finalHtml.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    return finalHtml;
}

function addMessage(content, isUser = false, animate = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;

    const formattedContent = formatContent(content);

    msgDiv.innerHTML = `
        <div class="message-content glass-panel">
            ${formattedContent}
        </div>
    `;

    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;

    if (animate && !isUser) {
        if (typeof typeHtmlEffect === 'function') {
            typeHtmlEffect(msgDiv.querySelector('.message-content'));
        } else {
            if (typeof window.autoplayTrackMaps === 'function') {
                window.autoplayTrackMaps();
            }
        }
    } else {
        if (typeof window.autoplayTrackMaps === 'function') {
            window.autoplayTrackMaps();
        }
    }

    // Mount any interactive 3D CAD viewer blocks inside this message
    if (typeof window.init3DBlueprints === 'function') {
        window.init3DBlueprints(msgDiv);
    }
}

function addTypingIndicator() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai-message typing-msg';
    msgDiv.innerHTML = `
        <div class="message-content glass-panel typing-indicator">
            <span></span><span></span><span></span>
        </div>
    `;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    return msgDiv;
}

const newChatBtn = document.getElementById('new-chat-btn');
const chatList = document.getElementById('chat-list');

// Auth elements
const authModal = document.getElementById('auth-modal');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const loginUsernameInput = document.getElementById('login-username');
const loginPasswordInput = document.getElementById('login-password');
const registerUsernameInput = document.getElementById('register-username');
const registerPasswordInput = document.getElementById('register-password');
const loginError = document.getElementById('login-error');
const registerError = document.getElementById('register-error');
const showRegisterBtn = document.getElementById('show-register-btn');
const showLoginBtn = document.getElementById('show-login-btn');
const logoutBtn = document.getElementById('logout-btn');
const userDisplayName = document.getElementById('user-display-name');

let chats = [];
let currentChatId = null;

function getToken() {
    return localStorage.getItem('f1_token');
}

function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + getToken()
    };
}

async function checkAuth() {
    console.log("checkAuth: Starting authentication check...");
    const token = getToken();
    console.log("checkAuth: Local storage token found?", !!token);
    if (!token) {
        authModal.style.display = 'flex';
        return;
    }

    try {
        console.log("checkAuth: Verifying token with server...");
        // Single call to verify session AND get username in one shot
        const meRes = await fetch('/api/auth/me', { headers: getHeaders() });
        console.log("checkAuth: /api/auth/me response status:", meRes.status);

        if (!meRes.ok) {
            console.log("checkAuth: Token verification failed, clearing local storage.");
            // Token is invalid or expired
            localStorage.removeItem('f1_token');
            localStorage.removeItem('f1_username');
            authModal.style.display = 'flex';
            return;
        }

        const me = await meRes.json();
        console.log("checkAuth: Authenticated user profile retrieved:", me.username, "is_admin:", me.is_admin);
        localStorage.setItem('f1_username', me.username);

        // Session is valid — show the dashboard
        authModal.style.display = 'none';
        userDisplayName.innerText = me.username;
        if (typeof updateAvatarDisplay === 'function') {
            updateAvatarDisplay();
        }

        // Load chats
        console.log("checkAuth: Fetching user chats...");
        const chatsRes = await fetch('/api/chats', { headers: getHeaders() });
        console.log("checkAuth: /api/chats response status:", chatsRes.status);
        chats = chatsRes.ok ? await chatsRes.json() : [];
        console.log("checkAuth: Loaded chats count:", chats.length);

        if (chats.length === 0) {
            console.log("checkAuth: No chats found, initializing default temporary chat...");
            const defaultChat = { id: 'chat_' + Date.now(), label: 'New Chat', messages: [], isTemp: true };
            chats.push(defaultChat);
            currentChatId = defaultChat.id;
            renderChatList();
            renderCurrentChat();
        } else {
            if (!currentChatId || !chats.find(c => c.id === currentChatId)) {
                currentChatId = chats[0].id;
            }
            console.log("checkAuth: Selecting current chat ID:", currentChatId);
            await selectChat(currentChatId);
        }
        console.log("checkAuth: Authentication and initialization finished successfully.");

    } catch (e) {
        console.error('checkAuth: Auth check failed with exception:', e);
        authModal.style.display = 'flex';
    }
}


async function selectChat(id) {
    currentChatId = id;
    renderChatList();

    const currentChat = chats.find(c => c.id === currentChatId);
    // If the chat is a local temporary chat (not in DB), render it directly (it has empty messages)
    if (!currentChat || currentChat.isTemp) {
        renderCurrentChat();
        return;
    }

    // Fetch historical messages from backend database
    try {
        const response = await fetch(`/api/chats/${id}/messages`, {
            headers: getHeaders()
        });
        if (response.ok) {
            const messages = await response.json();
            currentChat.messages = messages;
            renderCurrentChat();
        }
    } catch (e) {
        console.error("Failed to load chat messages:", e);
    }
}

async function deleteChat(id, event) {
    event.stopPropagation();
    if (confirm("Are you sure you want to delete this chat?")) {
        const chatToDelete = chats.find(c => c.id === id);
        // If it exists on the backend, delete it
        if (chatToDelete && !chatToDelete.isTemp) {
            try {
                await fetch(`/api/chats/${id}`, {
                    method: 'DELETE',
                    headers: getHeaders()
                });
            } catch (e) {
                console.error("Failed to delete chat:", e);
            }
        }

        chats = chats.filter(c => c.id !== id);
        if (chats.length === 0) {
            const defaultChat = {
                id: 'chat_' + Date.now(),
                label: 'New Chat',
                messages: [],
                isTemp: true
            };
            chats.push(defaultChat);
            currentChatId = defaultChat.id;
        } else if (currentChatId === id) {
            currentChatId = chats[0].id;
        }

        renderChatList();
        renderCurrentChat();
    }
}

function renderChatList() {
    chatList.innerHTML = '';
    chats.forEach(chat => {
        const item = document.createElement('div');
        item.className = `chat-list-item ${chat.id === currentChatId ? 'active' : ''}`;
        item.onclick = () => selectChat(chat.id);

        const titleSpan = document.createElement('span');
        titleSpan.innerHTML = `<i class="fa-regular fa-message"></i> ${chat.label}`;

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-chat-btn';
        deleteBtn.innerHTML = '<i class="fa-solid fa-trash-can"></i>';
        deleteBtn.onclick = (e) => deleteChat(chat.id, e);

        item.appendChild(titleSpan);
        item.appendChild(deleteBtn);
        chatList.appendChild(item);
    });
}

function renderCurrentChat() {
    chatHistory.innerHTML = '';
    const currentChat = chats.find(c => c.id === currentChatId);

    // Add welcome message if chat has no messages
    if (!currentChat || !currentChat.messages || currentChat.messages.length === 0) {
        addMessage('Welcome to the FastF1 AI Dashboard! 🏎️💨\n\nI can help you analyze race results, lap times, and telemetry. Try asking me something like: **"Who won the 2023 Bahrain Grand Prix?"** or **"What was the fastest lap in the 2023 Monaco race?"**', false);
        return;
    }

    currentChat.messages.forEach(msg => {
        addMessage(msg.content, msg.role === 'user');
    });

    if (typeof autoplayTrackMaps === 'function') {
        autoplayTrackMaps();
    }
}

async function handleSend() {
    const query = queryInput.value.trim();
    if (!query) return;

    const currentChat = chats.find(c => c.id === currentChatId);
    if (!currentChat) return;

    // Local echo of user message
    if (!currentChat.messages) currentChat.messages = [];
    currentChat.messages.push({ role: 'user', content: query });

    // Update local chat list label if it was a New Chat
    if (currentChat.label === 'New Chat') {
        currentChat.label = query.length > 22 ? query.substring(0, 20) + '...' : query;
        renderChatList();
    }

    // Clear welcome message if this is the first message in the chat
    if (currentChat.messages.length === 1) {
        chatHistory.innerHTML = '';
    }

    addMessage(query, true);
    queryInput.value = '';

    // Add typing indicator
    const typingIndicator = addTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ chat_id: currentChatId, query: query })
        });

        if (response.status === 401) {
            typingIndicator.remove();
            checkAuth();
            return;
        }

        const data = await response.json();

        // Remove typing indicator
        typingIndicator.remove();

        // Append assistant response
        currentChat.messages.push({ role: 'assistant', content: data.response });

        const wasTemp = currentChat.isTemp;

        // If this was a temporary chat, fetch list to update synced ID/label from DB
        if (wasTemp) {
            const chatsResponse = await fetch('/api/chats', {
                headers: getHeaders()
            });
            if (chatsResponse.ok) {
                const refreshedChats = await chatsResponse.json();
                if (refreshedChats.length > 0) {
                    chats = refreshedChats;
                    currentChatId = refreshedChats[0].id;
                }
            }
            await selectChat(currentChatId);
        } else {
            renderChatList();
            addMessage(data.response, false, true);
        }

    } catch (error) {
        typingIndicator.remove();
        const errMsg = "Sorry, I encountered an error connecting to the F1 backend server.";
        currentChat.messages.push({ role: 'assistant', content: errMsg });
        addMessage(errMsg, false);
        console.error(error);
    }
}

sendBtn.addEventListener('click', handleSend);
queryInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
});

newChatBtn.addEventListener('click', () => {
    const mostRecentChat = chats[0];
    const isMostRecentEmpty = mostRecentChat && (!mostRecentChat.messages || mostRecentChat.messages.length === 0);

    if (isMostRecentEmpty) {
        selectChat(mostRecentChat.id);
    } else {
        const newChat = {
            id: 'chat_' + Date.now(),
            label: 'New Chat',
            messages: [],
            isTemp: true
        };
        chats.unshift(newChat);
        currentChatId = newChat.id;
        renderChatList();
        renderCurrentChat();
    }
});

// ── Hidden Admin Portal Easter Egg ───────────────────────────────────────────
// Double click on checked flag logo inside normal login screen to open admin panel
const authLogo = document.querySelector('.auth-logo');
if (authLogo) {
    authLogo.style.cursor = 'pointer';
    authLogo.addEventListener('dblclick', () => {
        window.location.href = '/admin';
    });
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Escape key closes graph expansion modal
    if (e.key === 'Escape') {
        const graphModal = document.getElementById('graph-modal');
        if (graphModal && graphModal.style.display !== 'none') {
            closeGraphModal();
        }
    }

    if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'a') {
        const authModal = document.getElementById('auth-modal');
        if (authModal && authModal.style.display !== 'none') {
            window.location.href = '/admin';
        }
    }
});


// Auth Switchers
showRegisterBtn.onclick = (e) => {
    e.preventDefault();
    loginForm.style.display = 'none';
    registerForm.style.display = 'flex';
    document.getElementById('auth-subtitle').innerText = 'Create your F1 strategy account';
};

showLoginBtn.onclick = (e) => {
    e.preventDefault();
    registerForm.style.display = 'none';
    loginForm.style.display = 'flex';
    document.getElementById('auth-subtitle').innerText = 'Login to access your race strategy dashboard';
};

// Login submit
loginForm.onsubmit = async (e) => {
    e.preventDefault();
    loginError.style.display = 'none';

    const username = loginUsernameInput.value.trim();
    const password = loginPasswordInput.value;

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        if (response.ok) {
            localStorage.setItem('f1_token', data.token);
            localStorage.setItem('f1_username', data.username);
            loginUsernameInput.value = '';
            loginPasswordInput.value = '';
            checkAuth();
        } else {
            loginError.innerText = data.detail || 'Login failed';
            loginError.style.display = 'block';
        }
    } catch (err) {
        loginError.innerText = 'Unable to connect to the server';
        loginError.style.display = 'block';
    }
};

// Register submit
registerForm.onsubmit = async (e) => {
    e.preventDefault();
    registerError.style.display = 'none';

    const username = registerUsernameInput.value.trim();
    const password = registerPasswordInput.value;

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        if (response.ok) {
            registerUsernameInput.value = '';
            registerPasswordInput.value = '';
            // Auto switch to login
            registerForm.style.display = 'none';
            loginForm.style.display = 'flex';
            document.getElementById('auth-subtitle').innerText = 'Registration successful! Please log in.';
        } else {
            registerError.innerText = data.detail || 'Registration failed';
            registerError.style.display = 'block';
        }
    } catch (err) {
        registerError.innerText = 'Unable to connect to the server';
        registerError.style.display = 'block';
    }
};

// Logout button handler
if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                headers: getHeaders()
            });
        } catch (e) { }

        localStorage.removeItem('f1_token');
        localStorage.removeItem('f1_username');
        chats = [];
        currentChatId = null;
        checkAuth();
    });
}

// Graph modal expansion using event delegation
const graphModal = document.getElementById('graph-modal');
const expandedImg = document.getElementById('expanded-graph');
const closeModal = document.querySelector('.close-modal');

chatHistory.addEventListener('click', (e) => {
    if (e.target.tagName === 'IMG' && e.target.closest('.graph-container')) {
        const interactiveContainer = document.getElementById('modal-interactive-container');
        if (interactiveContainer) {
            interactiveContainer.style.display = 'none';
            interactiveContainer.innerHTML = '';
        }
        expandedImg.style.display = 'block';
        graphModal.style.display = "flex";
        expandedImg.src = e.target.src;
    }
});

function closeGraphModal() {
    const interactiveContainer = document.getElementById('modal-interactive-container');
    if (interactiveContainer) {
        const clone = interactiveContainer.querySelector('.interactive-track-map');
        if (clone) {
            pauseSimulation(clone);
        }
        const multiClone = interactiveContainer.querySelector('.interactive-multi-track-map');
        if (multiClone) {
            pauseMultiDriverSim(multiClone);
        }
        interactiveContainer.innerHTML = '';
        interactiveContainer.style.display = 'none';
    }
    graphModal.style.display = "none";
}

closeModal.addEventListener('click', closeGraphModal);
closeModal.addEventListener('touchstart', (e) => {
    e.preventDefault();
    closeGraphModal();
});

graphModal.addEventListener('click', (e) => {
    if (e.target === graphModal) {
        closeGraphModal();
    }
});

// Collapsible Sidebar
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');

function setSidebarCollapsed(collapsed) {
    if (collapsed) {
        sidebar.classList.add('collapsed');
    } else {
        sidebar.classList.remove('collapsed');
    }
    localStorage.setItem('f1_sidebar_collapsed', collapsed ? '1' : '0');
}

sidebarToggle.addEventListener('click', () => {
    setSidebarCollapsed(!sidebar.classList.contains('collapsed'));
});

// Mobile menu toggle button
const mobileMenuBtn = document.getElementById('mobile-menu-btn');
if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        setSidebarCollapsed(!sidebar.classList.contains('collapsed'));
    });
}

// Click away to close sidebar on mobile screens
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && sidebar) {
        const isOpen = !sidebar.classList.contains('collapsed');
        if (isOpen && !e.target.closest('#sidebar') && !e.target.closest('#mobile-menu-btn')) {
            setSidebarCollapsed(true);
        }
    }
});

// Restore persisted state on load
if (localStorage.getItem('f1_sidebar_collapsed') === '1') {
    setSidebarCollapsed(true);
}

function init() {
    checkAuth();
    if (typeof updateAvatarDisplay === 'function') {
        updateAvatarDisplay();
    }
}

init();

// Interactive Track Map Snapping Tooltips
window.handleTrackHover = function (evt, svgElem) {
    const rect = svgElem.getBoundingClientRect();
    const mouseX = evt.clientX - rect.left;
    const mouseY = evt.clientY - rect.top;

    const viewBox = svgElem.viewBox.baseVal;
    const svgX = (mouseX / rect.width) * viewBox.width;
    const svgY = (mouseY / rect.height) * viewBox.height;

    // Parse track telemetry data
    let points;
    try {
        points = JSON.parse(svgElem.getAttribute("data-telemetry-points"));
    } catch (e) {
        return;
    }

    if (!points || points.length === 0) return;

    // Find closest point by 2D distance
    let closestPoint = points[0];
    let minDistance = Math.pow(points[0].x - svgX, 2) + Math.pow(points[0].y - svgY, 2);

    for (let i = 1; i < points.length; i++) {
        const dist = Math.pow(points[i].x - svgX, 2) + Math.pow(points[i].y - svgY, 2);
        if (dist < minDistance) {
            minDistance = dist;
            closestPoint = points[i];
        }
    }

    // If the mouse is too far from the track (e.g. > 150px in SVG space), hide it
    if (minDistance > 22500) { // 150^2 = 22500
        window.handleTrackLeave(evt, svgElem);
        return;
    }

    // Position guide marker circle
    const marker = svgElem.querySelector("#track-guide-marker");
    if (marker) {
        marker.setAttribute("cx", closestPoint.x);
        marker.setAttribute("cy", closestPoint.y);
        marker.style.display = "block";
    }

    // Update tooltip
    const container = svgElem.closest(".interactive-track-map");
    const tooltip = container.querySelector(".track-tooltip");
    if (tooltip) {
        tooltip.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 6px; color: #ff1801; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px; font-size: 13px;">Telemetry Point</div>
            <div style="margin: 3px 0;">Speed: <strong style="color: #ffffff; font-size: 13px;">${Number(closestPoint.s).toFixed(2)} km/h</strong></div>
            <div style="margin: 3px 0;">Distance: <strong style="color: #ffffff;">${Number(closestPoint.d).toFixed(2)} m</strong></div>
            <div style="margin: 3px 0;">Gear: <strong style="color: #ffffff;">${closestPoint.g}</strong></div>
            <div style="margin: 3px 0;">Lap Time: <strong style="color: #ffffff;">${closestPoint.t}</strong></div>
        `;
        tooltip.style.display = "block";

        const containerRect = container.getBoundingClientRect();
        const x = evt.clientX - containerRect.left + 15;
        const y = evt.clientY - containerRect.top + 15;
        tooltip.style.left = x + "px";
        tooltip.style.top = y + "px";
    }
};

window.handleTrackLeave = function (evt, svgElem) {
    const marker = svgElem.querySelector("#track-guide-marker");
    if (marker) marker.style.display = "none";

    const container = svgElem.closest(".interactive-track-map");
    const tooltip = container.querySelector(".track-tooltip");
    if (tooltip) tooltip.style.display = "none";
};

// Interactive Telemetry Plot Snapping Tooltips
window.handleTelemetryHover = function (evt, svgElem) {
    const rect = svgElem.getBoundingClientRect();
    const mouseX = evt.clientX - rect.left;
    const mouseY = evt.clientY - rect.top;

    // Convert mouseX to SVG user space coordinate
    const viewBox = svgElem.viewBox.baseVal;
    const svgX = (mouseX / rect.width) * viewBox.width;

    // Retrieve margins and ranges
    const marginL = parseFloat(svgElem.getAttribute("data-margin-l"));
    const marginR = parseFloat(svgElem.getAttribute("data-margin-r"));
    const marginT = parseFloat(svgElem.getAttribute("data-margin-t"));
    const marginB = parseFloat(svgElem.getAttribute("data-margin-b"));
    const xMin = parseFloat(svgElem.getAttribute("data-x-min"));
    const xMax = parseFloat(svgElem.getAttribute("data-x-max"));
    const yMin = parseFloat(svgElem.getAttribute("data-y-min"));
    const yMax = parseFloat(svgElem.getAttribute("data-y-max"));

    const plotW = viewBox.width - marginL - marginR;
    const plotH = viewBox.height - marginT - marginB;

    // Check if mouse is within the plot area horizontally
    if (svgX < marginL || svgX > viewBox.width - marginR) {
        window.handleTelemetryLeave(evt, svgElem);
        return;
    }

    // Calculate the distance value corresponding to svgX
    const pctX = (svgX - marginL) / plotW;
    const targetDist = xMin + pctX * (xMax - xMin);

    // Parse telemetry data
    let telemetryData;
    try {
        telemetryData = JSON.parse(svgElem.getAttribute("data-telemetry"));
    } catch (e) {
        return;
    }

    if (!telemetryData || telemetryData.length === 0) return;

    // Find the closest point for each driver
    const activePoints = [];
    telemetryData.forEach((driverData, idx) => {
        const points = driverData.points;
        let closest = points[0];
        let minDist = Math.abs(points[0].d - targetDist);

        for (let i = 1; i < points.length; i++) {
            const diff = Math.abs(points[i].d - targetDist);
            if (diff < minDist) {
                minDist = diff;
                closest = points[i];
            }
        }
        activePoints.push({
            driver: driverData.name,
            color: driverData.color,
            point: closest
        });
    });

    if (activePoints.length === 0) return;

    // Update guide line position
    const guide = svgElem.querySelector("#telemetry-guide");
    if (guide) {
        guide.setAttribute("x1", svgX);
        guide.setAttribute("x2", svgX);
        guide.style.display = "block";
    }

    // Update driver circle markers
    activePoints.forEach((ap, idx) => {
        const marker = svgElem.querySelector(`.telemetry-marker[data-driver-index="${idx}"]`);
        if (marker) {
            // Scale values to SVG coordinates
            const cx = marginL + (ap.point.d - xMin) / (xMax - xMin) * plotW;
            const cy = (viewBox.height - marginB) - (ap.point.s - yMin) / (yMax - yMin) * plotH;
            marker.setAttribute("cx", cx.toFixed(1));
            marker.setAttribute("cy", cy.toFixed(1));
            marker.style.display = "block";
        }
    });

    // Update tooltip content
    const container = svgElem.closest(".interactive-telemetry-plot");
    const tooltip = container.querySelector(".telemetry-tooltip");
    if (tooltip) {
        let tooltipHtml = `
            <div style="font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px; font-size: 13px;">
                Distance: ${Number(activePoints[0].point.d).toFixed(2)} m
            </div>
        `;

        activePoints.forEach(ap => {
            tooltipHtml += `
                <div style="margin: 6px 0; display: flex; flex-direction: column;">
                    <span style="color: ${ap.color}; font-weight: bold; font-size: 12px;">${ap.driver}</span>
                    <span style="color: #ffffff; font-size: 12px; margin-top: 2px;">
                        Speed: <strong style="font-size: 13px;">${Number(ap.point.s).toFixed(2)} km/h</strong> | Gear: <strong>${ap.point.g}</strong>
                    </span>
                </div>
            `;
        });

        tooltip.innerHTML = tooltipHtml;
        tooltip.style.display = "block";

        const containerRect = container.getBoundingClientRect();
        const x = evt.clientX - containerRect.left + 15;
        const y = evt.clientY - containerRect.top + 15;
        tooltip.style.left = x + "px";
        tooltip.style.top = y + "px";
    }
};

window.handleTelemetryLeave = function (evt, svgElem) {
    const guide = svgElem.querySelector("#telemetry-guide");
    if (guide) guide.style.display = "none";

    const markers = svgElem.querySelectorAll(".telemetry-marker");
    markers.forEach(m => m.style.display = "none");

    const container = svgElem.closest(".interactive-telemetry-plot");
    const tooltip = container.querySelector(".telemetry-tooltip");
    if (tooltip) tooltip.style.display = "none";
};

// ── F1 Hot Lap Simulation Engine ─────────────────────────────────────────────

function initSimulationState(container) {
    if (container.simInitialized) return;

    const svg = container.querySelector('svg');
    if (!svg) return;

    let points = [];
    try {
        points = JSON.parse(svg.getAttribute('data-telemetry-points'));
    } catch (e) {
        console.error("Failed to parse telemetry points for simulation:", e);
        return;
    }

    container.simPoints = points;
    container.simIndex = 0;
    container.simPlaying = false;
    container.simAnimationId = null;
    container.simInitialized = true;

    // Force default speed selector to 1x programmatically (handles old chat history)
    const speedSelect = container.querySelector('.sim-speed');
    if (speedSelect) {
        speedSelect.value = "1";
    }

    // Configure slider to map 1-to-1 directly to the index of telemetry coordinates (removes jitter!)
    const slider = container.querySelector('.sim-slider');
    if (slider && points.length > 0) {
        slider.min = "0";
        slider.max = (points.length - 1).toString();
        slider.step = "1";
        slider.value = "0";
    }

    // Grab or build the simulated car marker in the SVG
    let marker = svg.querySelector('#sim-car-marker');
    if (!marker) {
        marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        marker.setAttribute('id', 'sim-car-marker');
        marker.setAttribute('r', '8');
        marker.setAttribute('fill', '#ffffff');
        marker.setAttribute('stroke', '#00ffff');
        marker.setAttribute('stroke-width', '2.5');
        marker.style.cssText = 'pointer-events: none; filter: drop-shadow(0 0 6px #00ffff); display: none;';
        const g = svg.querySelector('g');
        if (g) g.appendChild(marker);
    }
    container.simMarker = marker;
}

function playSimulation(container) {
    if (container.simPlaying) return;
    container.simPlaying = true;

    const playBtn = container.querySelector('.sim-play-btn');
    if (playBtn) playBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';

    if (container.simMarker) {
        container.simMarker.style.display = 'block';
    }

    let lastTime = null;

    function animateStep(timestamp) {
        if (!container.simPlaying) return;

        // Skip updates if container is hidden in background
        if (container.getBoundingClientRect().width === 0) {
            container.simAnimationId = requestAnimationFrame(animateStep);
            return;
        }

        if (!lastTime) {
            lastTime = timestamp;
            container.simAnimationId = requestAnimationFrame(animateStep);
            return;
        }

        const speedSelect = container.querySelector('.sim-speed');
        const speedMultiplier = speedSelect ? parseFloat(speedSelect.value) : 1;

        const elapsed = timestamp - lastTime;
        lastTime = timestamp;

        // Target sample rate: ~20Hz (approx 50ms per telemetry index point)
        const deltaIndex = (elapsed / 50) * speedMultiplier;
        container.simIndex += deltaIndex;

        if (container.simIndex >= container.simPoints.length) {
            container.simIndex = 0; // Loop the simulation
        }

        updateSimUI(container);
        container.simAnimationId = requestAnimationFrame(animateStep);
    }

    container.simAnimationId = requestAnimationFrame((t) => {
        lastTime = t;
        animateStep(t);
    });
}

function pauseSimulation(container) {
    container.simPlaying = false;
    if (container.simAnimationId) {
        cancelAnimationFrame(container.simAnimationId);
        container.simAnimationId = null;
    }
    const playBtn = container.querySelector('.sim-play-btn');
    if (playBtn) playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
}

function sliderManualInput(container, rawIndex) {
    initSimulationState(container);
    if (!container.simPoints || container.simPoints.length === 0) return;

    pauseSimulation(container);
    if (container.simMarker) {
        container.simMarker.style.display = 'block';
    }

    container.simIndex = Math.max(0, Math.min(container.simPoints.length - 1, parseFloat(rawIndex)));
    updateSimUI(container);
}

function updateSimUI(container) {
    const idx = Math.floor(container.simIndex);
    const pt1 = container.simPoints[idx];
    const pt2 = container.simPoints[idx + 1] || pt1;
    if (!pt1) return;

    const fraction = container.simIndex - idx;

    const p1x = parseFloat(pt1.x) || 0;
    const p1y = parseFloat(pt1.y) || 0;
    const p2x = parseFloat(pt2.x) || 0;
    const p2y = parseFloat(pt2.y) || 0;

    const interpX = p1x + (p2x - p1x) * fraction;
    const interpY = p1y + (p2y - p1y) * fraction;

    const interpSpeed = (parseFloat(pt1.s) || 0) + ((parseFloat(pt2.s) || 0) - (parseFloat(pt1.s) || 0)) * fraction;
    const interpDist = (parseFloat(pt1.d) || 0) + ((parseFloat(pt2.d) || 0) - (parseFloat(pt1.d) || 0)) * fraction;

    // Update SVG marker position
    if (container.simMarker) {
        container.simMarker.setAttribute('cx', interpX.toFixed(1));
        container.simMarker.setAttribute('cy', interpY.toFixed(1));
    }

    // Update timeline progress slider directly to index
    const slider = container.querySelector('.sim-slider');
    if (slider) {
        slider.value = idx;
    }

    // Update real-time telemetry dashboard values
    const speedVal = container.querySelector('.sim-speed-val');
    const gearVal = container.querySelector('.sim-gear-val');
    const distVal = container.querySelector('.sim-distance-val');
    const timeVal = container.querySelector('.sim-time-val');

    if (speedVal) speedVal.textContent = interpSpeed.toFixed(2) + " km/h";
    if (gearVal) gearVal.textContent = pt1.g;
    if (distVal) distVal.textContent = interpDist.toFixed(2) + " m";
    if (timeVal) timeVal.textContent = pt1.t;
}


// ── Multi-Driver Hot Lap Simulation Engine ────────────────────────────────────

function initMultiDriverSim(container) {
    if (container.multiSimInitialized) return;

    const svg = container.querySelector('svg[data-multi-telemetry]');
    if (!svg) return;

    let driversData = [];
    try {
        driversData = JSON.parse(svg.getAttribute('data-multi-telemetry'));
        // Backward compatibility: reconstruct ms values if missing from old chat history cache
        driversData.forEach(d => {
            if (d.points && d.points.length > 0 && typeof d.points[0].ms === 'undefined') {
                let totalMs = 90000; // default 90s fallback
                if (d.lt) {
                    const parts = d.lt.split(':');
                    if (parts.length === 2) {
                        const mins = parseFloat(parts[0]) || 0;
                        const secs = parseFloat(parts[1]) || 0;
                        totalMs = (mins * 60 + secs) * 1000;
                    } else {
                        const val = parseFloat(d.lt);
                        if (!isNaN(val)) totalMs = val * 1000;
                    }
                }
                const len = d.points.length;
                d.points.forEach((pt, idx) => {
                    pt.ms = len > 1 ? (idx / (len - 1)) * totalMs : 0;
                });
            }
        });
    } catch (e) {
        console.error('Failed to parse multi-driver telemetry:', e);
        return;
    }

    const controlsPane = container.querySelector('.driver-controls-pane');
    if (!controlsPane) return;
    controlsPane.innerHTML = ''; // clear placeholder

    const g = svg.querySelector('g') || svg;

    // Create independent simulation state for each driver
    const drivers = driversData.map((d, idx) => {
        let marker = svg.querySelector(`#multi-marker-${d.abbr}`);
        if (!marker) {
            marker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            marker.setAttribute('id', `multi-marker-${d.abbr}`);
            marker.setAttribute('r', '9');
            marker.setAttribute('fill', d.color);
            marker.setAttribute('stroke', '#ffffff');
            marker.setAttribute('stroke-width', '2');
            marker.style.cssText = `pointer-events:none;filter:drop-shadow(0 0 6px ${d.color});display:block;`;
            g.appendChild(marker);
        }

        let label = svg.querySelector(`#multi-label-${d.abbr}`);
        if (!label) {
            label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            label.setAttribute('id', `multi-label-${d.abbr}`);
            label.setAttribute('font-size', '9');
            label.setAttribute('font-family', 'monospace');
            label.setAttribute('font-weight', 'bold');
            label.setAttribute('fill', '#ffffff');
            label.setAttribute('text-anchor', 'middle');
            label.setAttribute('pointer-events', 'none');
            label.textContent = d.abbr;
            g.appendChild(label);
        }

        if (d.points && d.points.length > 0) {
            marker.setAttribute('cx', d.points[0].x);
            marker.setAttribute('cy', d.points[0].y);
            label.setAttribute('x', d.points[0].x);
            label.setAttribute('y', parseFloat(d.points[0].y) - 13);
        }

        // Build a control card for this driver
        const card = document.createElement('div');
        card.className = 'driver-control-card';
        card.dataset.driver = d.abbr;
        card.style.cssText = `background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-left:4px solid ${d.color}; border-radius:8px; padding:10px; display:flex; flex-direction:column; gap:6px; margin-bottom:4px; box-shadow:0 2px 8px rgba(0,0,0,0.15);`;

        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-weight:bold; font-size:12px; color:#fff;">${d.name} (${d.abbr})</span>
                    <div style="font-size:10px; color:#a0aab2; margin-top:1px;">${d.team}</div>
                </div>
                <span style="font-family:monospace; font-size:11px; color:${d.color}; font-weight:bold;">${d.lt}</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <button class="driver-play-btn" style="background:#e10600; border:none; color:white; width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center; cursor:pointer; transition:all 0.2s; flex-shrink:0;"><i class="fa-solid fa-play"></i></button>
                <input type="range" class="driver-slider" min="0" max="${d.points.length - 1}" value="0" style="flex-grow:1; height:4px; border-radius:2px; background:rgba(255,255,255,0.1); outline:none; cursor:pointer;">
                <select class="driver-speed" style="background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); color:white; border-radius:4px; padding:2px 4px; outline:none; font-size:10px; cursor:pointer; font-family:inherit;">
                    <option value="1">1x</option>
                    <option value="2">2x</option>
                    <option value="5">5x</option>
                    <option value="10">10x</option>
                </select>
            </div>
            <div style="display:flex; justify-content:space-between; font-family:monospace; font-size:10px; color:#a0aab2; margin-top:2px;">
                <span>Spd: <strong class="driver-speed-val" style="color:#00ffff;">0.0 km/h</strong></span>
                <span>Gear: <strong class="driver-gear-val" style="color:#fff;">-</strong></span>
                <span>Dist: <strong class="driver-dist-val" style="color:#fff;">0 m</strong></span>
                <span>Time: <strong class="driver-time-val" style="color:#ff1801;">0s</strong></span>
            </div>
        `;
        controlsPane.appendChild(card);

        const playBtn = card.querySelector('.driver-play-btn');
        const slider = card.querySelector('.driver-slider');
        const speedSelect = card.querySelector('.driver-speed');

        const driverState = {
            abbr: d.abbr,
            color: d.color,
            points: d.points,
            marker: marker,
            label: label,
            card: card,
            slider: slider,
            playBtn: playBtn,
            speedSelect: speedSelect,
            simTimeMs: 0,
            simPlaying: false,
            speedVal: card.querySelector('.driver-speed-val'),
            gearVal: card.querySelector('.driver-gear-val'),
            distVal: card.querySelector('.driver-dist-val'),
            timeVal: card.querySelector('.driver-time-val'),
        };

        playBtn.onclick = (e) => {
            e.stopPropagation();
            driverState.simPlaying = !driverState.simPlaying;
            playBtn.innerHTML = driverState.simPlaying ? '<i class="fa-solid fa-pause"></i>' : '<i class="fa-solid fa-play"></i>';
        };

        slider.oninput = (e) => {
            e.stopPropagation();
            driverState.simPlaying = false;
            playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
            const pt = d.points[parseFloat(e.target.value)];
            if (pt) {
                driverState.simTimeMs = pt.ms;
                updateDriverUITime(driverState, driverState.simTimeMs);
            }
        };

        slider.onclick = (e) => e.stopPropagation();
        speedSelect.onclick = (e) => e.stopPropagation();

        updateDriverUITime(driverState, 0);
        return driverState;
    });

    // Helper to find correct point index for a given elapsed time
    function findIndexForTime(points, timeMs) {
        let low = 0;
        let high = points.length - 2;
        let ans = 0;
        while (low <= high) {
            let mid = Math.floor((low + high) / 2);
            if (points[mid].ms <= timeMs) {
                ans = mid;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        return ans;
    }

    // Update coordinates, text values, and interpolate smoothly
    function updateDriverUITime(d, timeMs) {
        if (!d.points || d.points.length === 0) return;
        const maxTime = d.points[d.points.length - 1].ms || 0;
        const targetTime = Math.max(0, Math.min(maxTime, timeMs));

        // Find surrounding points
        const idx = findIndexForTime(d.points, targetTime);
        const pt1 = d.points[idx];
        const pt2 = d.points[idx + 1] || pt1;

        // Calculate interpolation factor
        let fraction = 0;
        const delta = pt2.ms - pt1.ms;
        if (delta > 0) {
            fraction = (targetTime - pt1.ms) / delta;
        }

        // Linear interpolation of coordinates (gives 60 FPS smooth sliding movement!)
        const p1x = parseFloat(pt1.x) || 0;
        const p1y = parseFloat(pt1.y) || 0;
        const p2x = parseFloat(pt2.x) || 0;
        const p2y = parseFloat(pt2.y) || 0;

        const interpX = p1x + (p2x - p1x) * fraction;
        const interpY = p1y + (p2y - p1y) * fraction;

        const interpSpeed = (parseFloat(pt1.s) || 0) + ((parseFloat(pt2.s) || 0) - (parseFloat(pt1.s) || 0)) * fraction;
        const interpDist = (parseFloat(pt1.d) || 0) + ((parseFloat(pt2.d) || 0) - (parseFloat(pt1.d) || 0)) * fraction;

        if (d.marker) {
            d.marker.setAttribute('cx', interpX.toFixed(1));
            d.marker.setAttribute('cy', interpY.toFixed(1));
        }
        if (d.label) {
            d.label.setAttribute('x', interpX.toFixed(1));
            d.label.setAttribute('y', (interpY - 13).toFixed(1));
        }
        if (d.slider) {
            d.slider.value = idx;
        }
        if (d.speedVal) d.speedVal.textContent = interpSpeed.toFixed(1) + ' km/h';
        if (d.gearVal) d.gearVal.textContent = pt1.g;
        if (d.distVal) d.distVal.textContent = interpDist.toFixed(0) + ' m';
        if (d.timeVal) {
            const mins = Math.floor(targetTime / 60000);
            const rem = targetTime % 60000;
            const secs = Math.floor(rem / 1000);
            const ms = Math.floor(rem % 1000);
            d.timeVal.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${ms.toString().padStart(3, '0')}`;
        }
    }

    // Programmatically ensure Universal Play button and Universal Speed dropdown exist (handles old cached database responses)
    const headerRow = container.querySelector('div[style*="border-bottom"]');
    if (headerRow) {
        let controlsDiv = headerRow.querySelector('.multi-controls-group') || headerRow.children[1];
        if (!controlsDiv) {
            controlsDiv = document.createElement('div');
            controlsDiv.style.cssText = 'display:flex;align-items:center;gap:12px;';
            headerRow.appendChild(controlsDiv);
        }
        controlsDiv.classList.add('multi-controls-group');
        controlsDiv.style.cssText = 'display:flex;align-items:center;gap:12px;';

        // 1. Ensure Universal Play Button exists
        let universalPlayBtn = controlsDiv.querySelector('.multi-universal-play-btn');
        if (!universalPlayBtn) {
            const txtEl = controlsDiv.querySelector('div[style*="text-align:right"]');
            universalPlayBtn = document.createElement('button');
            universalPlayBtn.className = 'multi-universal-play-btn';
            universalPlayBtn.innerHTML = '<i class="fa-solid fa-play"></i> Universal Play';
            universalPlayBtn.style.cssText = 'background:#e10600;border:none;color:#ffffff;font-family:Outfit,sans-serif;font-weight:600;font-size:11px;padding:6px 14px;border-radius:6px;cursor:pointer;display:flex;align-items:center;gap:6px;transition:all 0.2s;box-shadow:0 2px 8px rgba(225,6,0,0.35);';

            if (txtEl) {
                controlsDiv.insertBefore(universalPlayBtn, txtEl);
            } else {
                controlsDiv.appendChild(universalPlayBtn);
            }
        }

        // 2. Ensure Universal Speed Selector exists
        let universalSpeedSelect = controlsDiv.querySelector('.multi-universal-speed');
        if (!universalSpeedSelect) {
            universalSpeedSelect = document.createElement('select');
            universalSpeedSelect.className = 'multi-universal-speed';
            universalSpeedSelect.style.cssText = 'background:#1a1b1f !important;border:1px solid rgba(255,255,255,0.2);color:#ffffff !important;border-radius:6px;padding:6px 10px;outline:none;font-size:11px;font-family:Outfit,sans-serif;font-weight:600;cursor:pointer;transition:all 0.2s;min-width:105px;height:28px;';

            universalSpeedSelect.innerHTML = `
                <option value="1" style="background:#1a1b1f;color:#fff;">Speed: 1x</option>
                <option value="2" style="background:#1a1b1f;color:#fff;">Speed: 2x</option>
                <option value="3" style="background:#1a1b1f;color:#fff;">Speed: 3x</option>
                <option value="5" style="background:#1a1b1f;color:#fff;">Speed: 5x</option>
                <option value="10" style="background:#1a1b1f;color:#fff;">Speed: 10x</option>
            `;

            if (universalPlayBtn.nextSibling) {
                controlsDiv.insertBefore(universalSpeedSelect, universalPlayBtn.nextSibling);
            } else {
                controlsDiv.appendChild(universalSpeedSelect);
            }
        }

        // 3. Bind Universal Play Action
        universalPlayBtn.onclick = (e) => {
            e.stopPropagation();
            const anyPlaying = drivers.some(d => d.simPlaying);
            if (!anyPlaying) {
                drivers.forEach(d => {
                    d.simTimeMs = 0;
                });
            }
            drivers.forEach(d => {
                d.simPlaying = !anyPlaying;
                d.playBtn.innerHTML = d.simPlaying ? '<i class="fa-solid fa-pause"></i>' : '<i class="fa-solid fa-play"></i>';
            });
            universalPlayBtn.innerHTML = !anyPlaying ? '<i class="fa-solid fa-pause"></i> Universal Pause' : '<i class="fa-solid fa-play"></i> Universal Play';
        };

        // 4. Bind Universal Speed Action
        universalSpeedSelect.onchange = (e) => {
            e.stopPropagation();
            const val = e.target.value;
            drivers.forEach(d => {
                if (d.speedSelect) {
                    d.speedSelect.value = val;
                }
            });
        };
    }

    container.multiDrivers = drivers;
    container.multiSimInitialized = true;

    // Animation frame loop
    let lastTime = null;
    function animate(timestamp) {
        if (!container.isConnected && !document.body.contains(container)) {
            return;
        }
        // Throttling: Skip intensive calculations if container is hidden in background
        if (container.getBoundingClientRect().width === 0) {
            container.multiAnimationId = requestAnimationFrame(animate);
            return;
        }
        if (!lastTime) {
            lastTime = timestamp;
            container.multiAnimationId = requestAnimationFrame(animate);
            return;
        }
        const elapsed = timestamp - lastTime;
        lastTime = timestamp;

        drivers.forEach(d => {
            if (d.simPlaying) {
                const mult = parseFloat(d.speedSelect.value) || 1;
                d.simTimeMs += elapsed * mult;
                const maxTime = d.points[d.points.length - 1].ms || 0;
                if (d.simTimeMs >= maxTime) {
                    d.simTimeMs = 0;
                }
                updateDriverUITime(d, d.simTimeMs);
            }
        });

        container.multiAnimationId = requestAnimationFrame(animate);
    }
    container.multiAnimationId = requestAnimationFrame(animate);
}

function pauseMultiDriverSim(container) {
    if (container.multiDrivers) {
        container.multiDrivers.forEach(d => {
            d.simPlaying = false;
            if (d.playBtn) d.playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
        });
    }
    if (container.multiAnimationId) {
        cancelAnimationFrame(container.multiAnimationId);
        container.multiAnimationId = null;
    }
}

// Global helper to initialize newly loaded maps (single + multi driver)
window.autoplayTrackMaps = function () {
    // Single-driver maps
    const maps = chatHistory.querySelectorAll('.interactive-track-map');
    maps.forEach(map => {
        if (!map.simInitialized) {
            initSimulationState(map);
            updateSimUI(map);
            if (map.simMarker) {
                map.simMarker.style.display = 'block';
            }
        }
    });
    // Multi-driver maps
    const multiMaps = chatHistory.querySelectorAll('.interactive-multi-track-map');
    multiMaps.forEach(map => {
        if (!map.multiSimInitialized) {
            initMultiDriverSim(map);
        }
    });
};

// Event delegation listeners for interactive simulation control actions
document.addEventListener('click', (e) => {
    const playBtn = e.target.closest('.sim-play-btn');
    if (playBtn) {
        const singleContainer = playBtn.closest('.interactive-track-map');
        if (singleContainer) {
            initSimulationState(singleContainer);
            if (singleContainer.simPlaying) {
                pauseSimulation(singleContainer);
            } else {
                playSimulation(singleContainer);
            }
        }
        return;
    }

    // Expand to fullscreen when clicking on the track map layout/SVG or telemetry plot
    if (e.target.closest('.sim-controls') || e.target.closest('.sim-telemetry-dashboard') || e.target.closest('.close-sim-btn') || e.target.closest('button') || e.target.closest('select') || e.target.closest('input') || e.target.closest('.telemetry-tooltip') || e.target.closest('.track-tooltip')) {
        return;
    }

    const container = e.target.closest('.interactive-track-map, .interactive-telemetry-plot, .interactive-multi-track-map');
    if (container) {
        // Pause any active simulation in the chat log first
        if (container.classList.contains('interactive-track-map')) {
            pauseSimulation(container);
        } else if (container.classList.contains('interactive-multi-track-map')) {
            pauseMultiDriverSim(container);
        }

        const graphModal = document.getElementById('graph-modal');
        const expandedImg = document.getElementById('expanded-graph');
        const interactiveContainer = document.getElementById('modal-interactive-container');

        if (graphModal && expandedImg && interactiveContainer) {
            expandedImg.style.display = 'none';
            interactiveContainer.style.display = 'block';
            interactiveContainer.innerHTML = '';

            const clone = container.cloneNode(true);
            clone.style.width = '100%';
            clone.style.maxWidth = '100%';
            interactiveContainer.appendChild(clone);

            graphModal.style.display = "flex";

            if (clone.classList.contains('interactive-track-map')) {
                initSimulationState(clone);
                updateSimUI(clone);
                if (clone.simMarker) clone.simMarker.style.display = 'block';
            } else if (clone.classList.contains('interactive-multi-track-map')) {
                initMultiDriverSim(clone);
            }
        }
    }
});

document.addEventListener('input', (e) => {
    if (e.target.classList.contains('sim-slider')) {
        const singleContainer = e.target.closest('.interactive-track-map');
        if (singleContainer) {
            sliderManualInput(singleContainer, parseFloat(e.target.value));
        }
    }
});

document.addEventListener('change', (e) => {
    if (e.target.classList.contains('sim-speed')) {
        const singleContainer = e.target.closest('.interactive-track-map');
        if (singleContainer && singleContainer.simPlaying) {
            pauseSimulation(singleContainer);
            playSimulation(singleContainer);
        }
    }
});

// ── Gemini-style Typing/Streaming Effect for AI Responses ──────────────────────

function typeHtmlEffect(element, speed = 6) {
    function getTextNodes(node) {
        let textNodes = [];
        if (node.nodeType === Node.TEXT_NODE) {
            if (node.nodeValue.trim() !== '') {
                textNodes.push(node);
            }
        } else {
            for (let child of node.childNodes) {
                if (child.nodeType === Node.ELEMENT_NODE &&
                    (child.classList.contains('interactive-track-map') ||
                        child.classList.contains('interactive-telemetry-plot') ||
                        child.classList.contains('interactive-multi-track-map') ||
                        child.classList.contains('graph-container') ||
                        child.tagName === 'SVG' ||
                        child.hasAttribute('data-cad3d'))) {
                    continue;
                }
                textNodes = textNodes.concat(getTextNodes(child));
            }
        }
        return textNodes;
    }

    const textNodes = getTextNodes(element);
    const originalTexts = textNodes.map(node => {
        const val = node.nodeValue;
        node.nodeValue = ''; // Clear content temporarily
        return val;
    });

    let nodeIndex = 0;
    let charIndex = 0;

    function typeNext() {
        if (nodeIndex >= textNodes.length) {
            // Re-enable interactive elements setup once typing completes
            if (typeof window.autoplayTrackMaps === 'function') {
                window.autoplayTrackMaps();
            }
            // Initialize any 3D CAD viewers that appeared during typing
            if (typeof window.init3DBlueprints === 'function') {
                window.init3DBlueprints(element.closest('.message') || document);
            }
            return;
        }

        const node = textNodes[nodeIndex];
        const originalText = originalTexts[nodeIndex];

        node.nodeValue += originalText[charIndex];
        charIndex++;

        // Auto-scroll while typing
        chatHistory.scrollTop = chatHistory.scrollHeight;

        if (charIndex >= originalText.length) {
            nodeIndex++;
            charIndex = 0;
        }

        setTimeout(typeNext, speed);
    }

    typeNext();
}

// ── Profile Customization (Avatar selection) ───────────────────────────────────

function updateAvatarDisplay() {
    const avatar = document.getElementById('user-avatar');
    if (!avatar) return;

    const pfp = localStorage.getItem('f1_pfp_url') || 'linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05))';

    if (pfp.startsWith('linear-gradient') || pfp.startsWith('radial-gradient') || pfp.startsWith('#')) {
        avatar.style.background = pfp;
        avatar.innerHTML = '<i class="fa-solid fa-user"></i>';
    } else {
        avatar.style.background = 'transparent';
        avatar.innerHTML = `<img src="${pfp}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
    }
}

// Modal controls for pfp customization
const pfpModal = document.getElementById('pfp-modal');
const userAvatarBtn = document.getElementById('user-avatar');
const cancelPfpBtn = document.getElementById('cancel-pfp-btn');
const savePfpBtn = document.getElementById('save-pfp-btn');
const customPfpInput = document.getElementById('custom-pfp-input');

let selectedPfpVal = '';

if (userAvatarBtn) {
    userAvatarBtn.addEventListener('click', () => {
        if (pfpModal) {
            // Restore current state to modal input
            const curPfp = localStorage.getItem('f1_pfp_url') || '';
            if (curPfp && !curPfp.startsWith('linear-gradient')) {
                customPfpInput.value = curPfp;
            } else {
                customPfpInput.value = '';
            }
            selectedPfpVal = curPfp;

            // Highlight selected preset if it matches
            const presets = pfpModal.querySelectorAll('.pfp-preset');
            presets.forEach(p => {
                if (p.getAttribute('data-val') === curPfp) {
                    p.style.borderColor = 'var(--f1-red)';
                    p.style.transform = 'scale(1.1)';
                } else {
                    p.style.borderColor = 'transparent';
                    p.style.transform = 'none';
                }
            });

            pfpModal.style.display = 'flex';
        }
    });
}

// Preset selection
if (pfpModal) {
    const presets = pfpModal.querySelectorAll('.pfp-preset');
    presets.forEach(preset => {
        preset.addEventListener('click', () => {
            presets.forEach(p => {
                p.style.borderColor = 'transparent';
                p.style.transform = 'none';
            });
            preset.style.borderColor = 'var(--f1-red)';
            preset.style.transform = 'scale(1.1)';
            selectedPfpVal = preset.getAttribute('data-val');
            customPfpInput.value = ''; // Clear custom input when preset is clicked
        });
    });
}

if (cancelPfpBtn) {
    cancelPfpBtn.addEventListener('click', () => {
        if (pfpModal) pfpModal.style.display = 'none';
    });
}

if (savePfpBtn) {
    savePfpBtn.addEventListener('click', () => {
        const customUrl = customPfpInput.value.trim();
        if (customUrl) {
            localStorage.setItem('f1_pfp_url', customUrl);
        } else if (selectedPfpVal) {
            localStorage.setItem('f1_pfp_url', selectedPfpVal);
        }
        updateAvatarDisplay();
        if (pfpModal) pfpModal.style.display = 'none';
    });
}

if (pfpModal) {
    pfpModal.addEventListener('click', (e) => {
        if (e.target === pfpModal) {
            pfpModal.style.display = 'none';
        }
    });
}


// On page load, initialize any 3D CAD viewers that may exist from reloaded chat history
document.addEventListener('DOMContentLoaded', () => {
    if (typeof window.init3DBlueprints === 'function') {
        window.init3DBlueprints(document);
    }
});
