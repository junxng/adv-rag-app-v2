import React from 'react';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  source?: string;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ role, content, source }) => {
  return (
    <div className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`p-3 rounded-lg max-w-[80%] ${
          role === 'user'
            ? 'bg-primary-600 text-white'
            : 'bg-gray-100 text-gray-800'
        }`}
      >
        <div className="whitespace-pre-wrap">{content}</div>
        
        {source && (
          <div className={`text-xs mt-1 ${
            role === 'user' ? 'text-primary-200' : 'text-gray-500'
          }`}>
            Source: {source}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
