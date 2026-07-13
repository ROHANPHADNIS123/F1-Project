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

let chats = [];
let currentChatId = null;

function saveChats() {
    localStorage.setItem('f1_chats', JSON.stringify(chats));
}

function createDefaultChat() {
    return {
        id: 'chat_' + Date.now(),
        label: 'New Chat',
        messages: [
            {
                role: 'assistant',
                content: 'Welcome to the FastF1 AI Dashboard! 🏎️💨\n\nI can help you analyze race results, lap times, and telemetry. Try asking me something like: **"Who won the 2023 Bahrain Grand Prix?"** or **"What was the fastest lap in the 2023 Monaco race?"**'
            }
        ]
    };
}

function selectChat(id) {
    currentChatId = id;
    renderChatList();
    renderCurrentChat();
}

function deleteChat(id, event) {
    event.stopPropagation();
    if (confirm("Are you sure you want to delete this chat?")) {
        chats = chats.filter(c => c.id !== id);
        if (chats.length === 0) {
            const defaultChat = createDefaultChat();
            chats.push(defaultChat);
            currentChatId = defaultChat.id;
        } else if (currentChatId === id) {
            currentChatId = chats[0].id;
        }
        saveChats();
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
    if (currentChat) {
        currentChat.messages.forEach(msg => {
            addMessage(msg.content, msg.role === 'user');
        });
    }
}

async function handleSend() {
    const query = queryInput.value.trim();
    if (!query) return;

    const currentChat = chats.find(c => c.id === currentChatId);
    if (!currentChat) return;

    // Get chat history before adding the new message (excluding welcome message context if desired, but sending it is fine)
    const history = currentChat.messages.map(m => ({
        role: m.role,
        content: m.content
    }));

    // Update state with user message
    const isFirstUserMessage = currentChat.messages.filter(m => m.role === 'user').length === 0;
    currentChat.messages.push({ role: 'user', content: query });
    
    // Label the chat based on the first query
    if (isFirstUserMessage) {
        currentChat.label = query.length > 22 ? query.substring(0, 20) + '...' : query;
        renderChatList();
    }
    
    saveChats();
    renderCurrentChat();
    queryInput.value = '';
    
    // Add typing indicator
    const typingIndicator = addTypingIndicator();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, history: history })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        typingIndicator.remove();
        
        // Save AI response to state
        currentChat.messages.push({ role: 'assistant', content: data.response });
        saveChats();
        
        // Update UI
        addMessage(data.response, false);
    } catch (error) {
        typingIndicator.remove();
        const errMsg = "Sorry, I encountered an error connecting to the F1 backend server.";
        currentChat.messages.push({ role: 'assistant', content: errMsg });
        saveChats();
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
    const isMostRecentEmpty = mostRecentChat && mostRecentChat.messages.filter(m => m.role === 'user').length === 0;
    
    if (isMostRecentEmpty) {
        selectChat(mostRecentChat.id);
    } else {
        const newChat = createDefaultChat();
        chats.unshift(newChat);
        saveChats();
        selectChat(newChat.id);
    }
});

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

// Initialize on load
function init() {
    const stored = localStorage.getItem('f1_chats');
    if (stored) {
        try {
            chats = JSON.parse(stored);
        } catch (e) {
            chats = [];
        }
    }
    
    if (chats.length === 0) {
        const defaultChat = createDefaultChat();
        chats.push(defaultChat);
        currentChatId = defaultChat.id;
        saveChats();
    } else {
        currentChatId = chats[0].id;
    }
    
    renderChatList();
    renderCurrentChat();
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
            <div style="margin: 3px 0;">Speed: <strong style="color: #ffffff; font-size: 13px;">${closestPoint.s} km/h</strong></div>
            <div style="margin: 3px 0;">Distance: <strong style="color: #ffffff;">${closestPoint.d} m</strong></div>
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
                Distance: ${Math.round(activePoints[0].point.d)} m
            </div>
        `;
        
        activePoints.forEach(ap => {
            tooltipHtml += `
                <div style="margin: 6px 0; display: flex; flex-direction: column;">
                    <span style="color: ${ap.color}; font-weight: bold; font-size: 12px;">${ap.driver}</span>
                    <span style="color: #ffffff; font-size: 12px; margin-top: 2px;">
                        Speed: <strong style="font-size: 13px;">${Math.round(ap.point.s)} km/h</strong> | Gear: <strong>${ap.point.g}</strong>
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
