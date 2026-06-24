const chatHistory = document.getElementById('chat-history');
const queryInput = document.getElementById('query-input');
const sendBtn = document.getElementById('send-btn');

function addMessage(content, isUser = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;
    
    let avatarHtml = isUser 
        ? `<div class="avatar"><i class="fa-solid fa-user"></i></div>` 
        : `<div class="avatar ai-avatar"><i class="fa-solid fa-robot"></i></div>`;
        
    // Format text nicely (basic markdown handling for bold and line breaks)
    const formattedContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');

    msgDiv.innerHTML = `
        ${avatarHtml}
        <div class="message-content glass-panel">
            <p>${formattedContent}</p>
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

async function handleSend() {
    const query = queryInput.value.trim();
    if (!query) return;

    // Add user message
    addMessage(query, true);
    queryInput.value = '';
    
    // Add typing indicator
    const typingIndicator = addTypingIndicator();
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        typingIndicator.remove();
        
        // Add AI response
        addMessage(data.response, false);
    } catch (error) {
        typingIndicator.remove();
        addMessage("Sorry, I encountered an error connecting to the F1 backend server.", false);
        console.error(error);
    }
}

sendBtn.addEventListener('click', handleSend);
queryInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSend();
});
