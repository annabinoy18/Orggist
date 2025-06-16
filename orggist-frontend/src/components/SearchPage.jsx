import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import './SearchPage.css';
import TopBar from './TopBar';
import { marked } from 'marked';

const SearchPage = () => {
  const [user] = useState({
    name: "Test User",
    picture: "https://via.placeholder.com/40",
  });

  const [webSearch, setWebSearch] = useState(false);
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showOptions, setShowOptions] = useState(false);

  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async () => {
    if (!query.trim()) return;

    console.log("Web search toggle value:", webSearch);

    const userMessage = { role: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    setQuery('');
    setIsLoading(true);

    // Add a placeholder for assistant message
    let assistantMessage = { role: 'assistant', content: '' };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      const response = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ 
          query, 
          web_search: webSearch,
          similarity_threshold: 0.3 
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Something went wrong!");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let finalText = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        finalText += chunk;

        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1].content = finalText;
          return updated;
        });

        scrollToBottom();
      }
    } catch (err) {
      console.error("Error while fetching:", err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "⚠️ Sorry, something went wrong."
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleWebSearch = () => {
    setWebSearch(prev => !prev);
    console.log("Web search toggled to:", !webSearch);
  };

  return (
    <div className="search-page">
      <TopBar user={user} />

      <main className="chat-container">
        <div className="chat-header">
          <h2>Welcome, {user.name.split(' ')[0]} 👋</h2>
          <div className="menu-container">
            <button
              className="menu-toggle"
              onClick={() => setShowOptions(prev => !prev)}
            >
              ⋮
            </button>

            {showOptions && (
              <div className="dropdown-options">
                <div className="dropdown-item">
                  <span>Web Search</span>
                  <label className="switch">
                    <input
                      type="checkbox"
                      checked={webSearch}
                      onChange={toggleWebSearch}
                    />
                    <span className="slider round"></span>
                  </label>
                </div>
                <Link to="/upload" className="dropdown-item link-item">
                  <span>File Manage</span>
                </Link>
              </div>
            )}
          </div>
        </div>

        <div className="chat-box">
          <div className="chat-box-inner">
            {messages.map((msg, i) => (
              <div key={i} className={`chat-message ${msg.role}`}>
                <div
                  className="bubble"
                  dangerouslySetInnerHTML={{ __html: marked.parse(msg.content) }}
                ></div>
              </div>
            ))}
            {isLoading && (
              <div className="chat-message assistant">
                <div className="bubble typing">Typing...</div>
              </div>
            )}
            <div ref={chatEndRef}></div>
          </div>
        </div>

        <div className="chat-input-area">
        <div className="chat-input-inner">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything..."
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            disabled={isLoading}
          />
          <button onClick={handleSend} disabled={isLoading}>↗</button>
        </div>
      </div>
      </main>
    </div>
  );
};

export default SearchPage;
