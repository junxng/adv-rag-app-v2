document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const chatForm = document.getElementById('chatForm');
    const userInput = document.getElementById('userInput');
    const chatContainer = document.getElementById('chatContainer');
    const resetChatBtn = document.getElementById('resetChatBtn');
    const exampleQuestions = document.querySelectorAll('.example-question');
    
    // Add event listeners
    chatForm.addEventListener('submit', handleChatSubmit);
    resetChatBtn.addEventListener('click', resetChat);
    exampleQuestions.forEach(question => {
        question.addEventListener('click', handleExampleQuestion);
    });
    
    // Focus on input field
    userInput.focus();
    
    // Scroll to bottom of chat
    scrollToBottom();
    
    /**
     * Handle chat form submission
     * @param {Event} e - Form submit event
     */
    function handleChatSubmit(e) {
        e.preventDefault();
        
        // Get user message
        const message = userInput.value.trim();
        
        // Check if message is empty
        if (!message) return;
        
        // Add user message to chat
        addMessageToChat('user', message);
        
        // Clear input field
        userInput.value = '';
        
        // Add loading indicator
        const loadingId = addLoadingIndicator();
        
        // Send message to server
        sendMessageToServer(message)
            .then(response => {
                // Remove loading indicator
                removeLoadingIndicator(loadingId);
                
                // Add assistant response to chat
                addMessageToChat('assistant', response.message, response.source);
            })
            .catch(error => {
                // Remove loading indicator
                removeLoadingIndicator(loadingId);
                
                // Add error message to chat
                addMessageToChat('assistant', 'Sorry, there was an error processing your request. Please try again.', 'Error');
                console.error('Error:', error);
            });
    }
    
    /**
     * Send message to server API
     * @param {string} message - User message
     * @returns {Promise} - Response promise
     */
    function sendMessageToServer(message) {
        return fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        });
    }
    
    /**
     * Add a message to the chat container
     * @param {string} role - 'user' or 'assistant'
     * @param {string} content - Message content
     * @param {string} source - Source of information (for assistant messages)
     */
    function addMessageToChat(role, content, source = null) {
        // Create message element
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', role);
        
        // Create message content
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content');
        
        // Add message text
        const paragraph = document.createElement('p');
        paragraph.textContent = content;
        contentDiv.appendChild(paragraph);
        
        // Add source badge for assistant messages
        if (role === 'assistant' && source) {
            const sourceDiv = document.createElement('div');
            sourceDiv.classList.add('message-source');
            
            const sourceBadge = document.createElement('span');
            sourceBadge.classList.add('badge');
            
            // Set badge color based on source
            if (source === 'Database') {
                sourceBadge.classList.add('bg-primary');
            } else if (source === 'Web Search') {
                sourceBadge.classList.add('bg-success');
            } else if (source === 'Knowledge Base') {
                sourceBadge.classList.add('bg-warning');
                sourceBadge.style.color = '#212529';
            } else {
                sourceBadge.classList.add('bg-secondary');
            }
            
            sourceBadge.textContent = source;
            sourceDiv.appendChild(sourceBadge);
            contentDiv.appendChild(sourceDiv);
        }
        
        // Add content to message
        messageDiv.appendChild(contentDiv);
        
        // Add message to chat container
        chatContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        scrollToBottom();
    }
    
    /**
     * Add loading indicator to chat
     * @returns {string} - ID of the loading indicator
     */
    function addLoadingIndicator() {
        const id = 'loading-' + Date.now();
        
        const loadingDiv = document.createElement('div');
        loadingDiv.classList.add('chat-message', 'assistant');
        loadingDiv.id = id;
        
        const contentDiv = document.createElement('div');
        contentDiv.classList.add('message-content', 'loading-indicator');
        
        const dotsDiv = document.createElement('div');
        dotsDiv.classList.add('loading-dots');
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            dotsDiv.appendChild(dot);
        }
        
        contentDiv.appendChild(dotsDiv);
        loadingDiv.appendChild(contentDiv);
        chatContainer.appendChild(loadingDiv);
        
        scrollToBottom();
        
        return id;
    }
    
    /**
     * Remove loading indicator from chat
     * @param {string} id - ID of the loading indicator
     */
    function removeLoadingIndicator(id) {
        const loadingDiv = document.getElementById(id);
        if (loadingDiv) {
            loadingDiv.remove();
        }
    }
    
    /**
     * Scroll to bottom of chat container
     */
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    /**
     * Reset chat history
     */
    function resetChat() {
        // Clear chat container except for first welcome message
        while (chatContainer.children.length > 1) {
            chatContainer.removeChild(chatContainer.lastChild);
        }
        
        // Reset chat history on server
        fetch('/api/reset', {
            method: 'POST'
        }).catch(error => {
            console.error('Error resetting chat:', error);
        });
        
        // Focus on input field
        userInput.focus();
    }
    
    /**
     * Handle example question click
     * @param {Event} e - Click event
     */
    function handleExampleQuestion(e) {
        const question = e.currentTarget.dataset.question;
        userInput.value = question;
        userInput.focus();
    }
});
