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

function addMessage(content, isUser = false) {
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
    } catch(e) {
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
            } catch(e) {
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
    
    renderCurrentChat();
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
            renderCurrentChat();
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
// Removed as requested


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
    } catch(err) {
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
    } catch(err) {
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
        } catch(e) {}
        
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
        graphModal.style.display = "flex";
        expandedImg.src = e.target.src;
    }
});

closeModal.addEventListener('click', () => {
    graphModal.style.display = "none";
});

graphModal.addEventListener('click', (e) => {
    if (e.target === graphModal) {
        graphModal.style.display = "none";
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

// Restore persisted state on load
if (localStorage.getItem('f1_sidebar_collapsed') === '1') {
    setSidebarCollapsed(true);
}

function init() {
    checkAuth();
}

init();

// Interactive Track Map Snapping Tooltips
window.handleTrackHover = function(evt, svgElem) {
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
    } catch(e) {
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

window.handleTrackLeave = function(evt, svgElem) {
    const marker = svgElem.querySelector("#track-guide-marker");
    if (marker) marker.style.display = "none";
    
    const container = svgElem.closest(".interactive-track-map");
    const tooltip = container.querySelector(".track-tooltip");
    if (tooltip) tooltip.style.display = "none";
};

// Interactive Telemetry Plot Snapping Tooltips
window.handleTelemetryHover = function(evt, svgElem) {
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
    } catch(e) {
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

window.handleTelemetryLeave = function(evt, svgElem) {
    const guide = svgElem.querySelector("#telemetry-guide");
    if (guide) guide.style.display = "none";
    
    const markers = svgElem.querySelectorAll(".telemetry-marker");
    markers.forEach(m => m.style.display = "none");
    
    const container = svgElem.closest(".interactive-telemetry-plot");
    const tooltip = container.querySelector(".telemetry-tooltip");
    if (tooltip) tooltip.style.display = "none";
};
