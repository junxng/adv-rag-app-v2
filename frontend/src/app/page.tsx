'use client';

import { useState, useRef, useEffect } from 'react';
import ChatMessage from '@/components/ChatMessage';
import ChatInput from '@/components/ChatInput';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  source?: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I\'m your tech support assistant. How can I help you today?',
      source: 'System'
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return;

    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: message }]);
    setIsLoading(true);

    try {
      // Send to API and get response
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();

      // Add bot response to chat
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message,
        source: data.source
      }]);
    } catch (error) {
      console.error('Error:', error);
      
      // Add error message
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again later.',
        source: 'Error'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      await fetch('/api/reset', {
        method: 'POST'
      });
      
      setMessages([{
        role: 'assistant',
        content: 'Chat history has been reset. How can I help you today?',
        source: 'System'
      }]);
    } catch (error) {
      console.error('Error resetting chat:', error);
    }
  };

  return (
    <main className="container mx-auto max-w-4xl p-4 h-screen flex flex-col">
      <header className="text-center py-4">
        <h1 className="text-3xl font-bold text-primary-700">Tech Support Chatbot</h1>
      </header>
      
      <div className="flex-1 bg-white rounded-lg shadow-md flex flex-col overflow-hidden">
        <div className="flex-1 p-4 overflow-y-auto scrollbar-thin">
          {messages.map((message, index) => (
            <ChatMessage
              key={index}
              role={message.role}
              content={message.content}
              source={message.source}
            />
          ))}
          {isLoading && (
            <div className="flex items-center space-x-2 p-3 max-w-[80%] bg-gray-100 rounded-lg text-gray-500">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
          
          <div className="mt-2 text-right">
            <button
              onClick={handleReset}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Reset Chat
            </button>
          </div>
        </div>
      </div>
      
      <footer className="text-center py-4 text-sm text-gray-500">
        Powered by FastAPI, Next.js, and Pinecone
      </footer>
    </main>
  );
}
