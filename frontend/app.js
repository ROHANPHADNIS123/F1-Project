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
                if (line.startsWith('###')) {
                    processedHtml.push(`<h3>${line.replace('###', '').trim()}</h3>`);
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
    
    let avatarHtml = isUser 
        ? `<div class="avatar"><i class="fa-solid fa-user"></i></div>` 
        : `<div class="avatar ai-avatar"><i class="fa-solid fa-robot"></i></div>`;
        
    const formattedContent = formatContent(content);

    msgDiv.innerHTML = `
        ${avatarHtml}
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
        <div class="avatar ai-avatar"><i class="fa-solid fa-robot"></i></div>
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
