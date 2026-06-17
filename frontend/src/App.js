import React, { useState, useEffect, useRef } from "react";
import {
  Send,
  Database,
  Activity,
  User,
  Bot,
  Sparkles,
  Trash2,
  Plus
} from "lucide-react";
import { checkHealth, queryRAG } from "./services/api";

export default function App() {
  // State for multiple chat sessions, loaded from localStorage
  const [chats, setChats] = useState(() => {
    const saved = localStorage.getItem("talentai_chats");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error("Failed to parse chats from localStorage:", e);
      }
    }
    const initialId = Date.now().toString();
    return [{ id: initialId, title: "New Chat", messages: [] }];
  });

  const [activeChatId, setActiveChatId] = useState(() => {
    const saved = localStorage.getItem("talentai_active_chat_id");
    if (saved) return saved;
    return chats[0]?.id || "";
  });

  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [backendHealth, setBackendHealth] = useState({
    status: "checking",
    database: "checking",
    indexed_candidates: 0,
    error: null
  });

  const chatEndRef = useRef(null);

  // Sync chats to localStorage
  useEffect(() => {
    localStorage.setItem("talentai_chats", JSON.stringify(chats));
  }, [chats]);

  // Sync activeChatId to localStorage
  useEffect(() => {
    localStorage.setItem("talentai_active_chat_id", activeChatId);
  }, [activeChatId]);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chats, activeChatId, loading]);

  // Poll backend health status
  useEffect(() => {
    let active = true;
    const loadHealth = async () => {
      const health = await checkHealth();
      if (active) {
        setBackendHealth(health);
      }
    };

    loadHealth();
    const interval = setInterval(loadHealth, 10000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // Retrieve active chat messages
  const activeChat = chats.find(c => c.id === activeChatId) || chats[0] || { messages: [] };
  const messages = activeChat.messages;

  // Create a new chat session
  const handleNewChat = () => {
    const newId = Date.now().toString();
    const newChatObj = { id: newId, title: "New Chat", messages: [] };
    setChats((prev) => [newChatObj, ...prev]);
    setActiveChatId(newId);
  };

  // Delete a chat session
  const handleDeleteChat = (chatId, event) => {
    event.stopPropagation(); // Prevent selecting the chat when clicking delete

    const remainingChats = chats.filter((c) => c.id !== chatId);

    if (remainingChats.length === 0) {
      const newId = Date.now().toString();
      const defaultChat = { id: newId, title: "New Chat", messages: [] };
      setChats([defaultChat]);
      setActiveChatId(newId);
    } else {
      setChats(remainingChats);
      if (activeChatId === chatId) {
        setActiveChatId(remainingChats[0].id);
      }
    }
  };

  // Handle message submit
  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || loading) return;

    const userMessage = {
      sender: "user",
      text: inputText.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const updatedMessages = [...messages, userMessage];

    // Optimistically update messages locally
    setChats((prevChats) =>
      prevChats.map((chat) => {
        if (chat.id === activeChatId) {
          // If first message, update chat title to user query
          let newTitle = chat.title;
          if (chat.title === "New Chat") {
            newTitle = userMessage.text.length > 22
              ? userMessage.text.substring(0, 22) + "..."
              : userMessage.text;
          }
          return { ...chat, title: newTitle, messages: updatedMessages };
        }
        return chat;
      })
    );

    setInputText("");
    setLoading(true);

    try {
      // Send query to backend with static k=5
      const result = await queryRAG(userMessage.text, 5);
      const botMessage = {
        sender: "bot",
        text: result.response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setChats((prevChats) =>
        prevChats.map((chat) => {
          if (chat.id === activeChatId) {
            return { ...chat, messages: [...updatedMessages, botMessage] };
          }
          return chat;
        })
      );
    } catch (err) {
      const errorMessage = {
        sender: "bot",
        text: `❌ Error connecting to server: ${err.message}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: true
      };

      setChats((prevChats) =>
        prevChats.map((chat) => {
          if (chat.id === activeChatId) {
            return { ...chat, messages: [...updatedMessages, errorMessage] };
          }
          return chat;
        })
      );
    } finally {
      setLoading(false);
    }
  };

  // Helper to render markdown-like responses natively
  const formatResponse = (text) => {
    if (!text) return "";
    const lines = text.split("\n");
    return (
      <div className="prose">
        {lines.map((line, idx) => {
          let cleanLine = line.trim();
          if (!cleanLine) return <div key={idx} className="h-2" />;

          // Headers: ## Header or ### Header
          if (cleanLine.startsWith("### ") || cleanLine.startsWith("###")) {
            return (
              <h4 key={idx} style={{ fontFamily: "var(--font-display)" }} className="text-white font-semibold text-sm mt-3 mb-1">
                {cleanLine.replace(/^###\s*/, "")}
              </h4>
            );
          }
          if (cleanLine.startsWith("## ") || cleanLine.startsWith("##")) {
            return (
              <h3 key={idx} style={{ fontFamily: "var(--font-display)" }} className="text-white font-bold text-base mt-4 mb-2">
                {cleanLine.replace(/^##\s*/, "")}
              </h3>
            );
          }
          if (cleanLine.startsWith("**") && cleanLine.endsWith("**")) {
            return (
              <h3 key={idx} style={{ fontFamily: "var(--font-display)" }} className="text-violet-400 font-bold text-base mt-3 mb-1">
                {cleanLine.replace(/\*\*/g, "")}
              </h3>
            );
          }

          // Bullet lists: * bullet or - bullet
          if (cleanLine.startsWith("* ") || cleanLine.startsWith("- ")) {
            const bulletText = cleanLine.replace(/^[\*\-]\s+/, "");
            const parts = bulletText.split("**");
            return (
              <li key={idx} className="ml-4 list-disc text-sm text-slate-300 mb-1">
                {parts.map((part, pIdx) =>
                  pIdx % 2 === 1 ? (
                    <strong key={pIdx} className="text-white font-semibold">{part}</strong>
                  ) : (
                    part
                  )
                )}
              </li>
            );
          }

          // Paragraphs with inline **bold** text
          const parts = cleanLine.split("**");
          return (
            <p key={idx} className="text-sm text-slate-300 mb-2 leading-relaxed">
              {parts.map((part, pIdx) =>
                pIdx % 2 === 1 ? (
                  <strong key={pIdx} className="text-white font-semibold">{part}</strong>
                ) : (
                  part
                )
              )}
            </p>
          );
        })}
      </div>
    );
  };

  return (
    <div style={{ height: "100vh", width: "100vw", display: "flex", backgroundColor: "#060913" }}>

      {/* Sidebar Section */}
      <div className="glass-sidebar" style={{ width: "320px", display: "flex", flexDirection: "column", padding: "24px" }}>

        {/* Logo Title */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "24px" }}>
          <div style={{
            background: "var(--gradient-btn)",
            padding: "8px",
            borderRadius: "10px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}>
            <Sparkles size={20} color="#fff" />
          </div>
          <span style={{
            fontFamily: "var(--font-display)",
            fontWeight: 800,
            fontSize: "1.4rem",
            letterSpacing: "-0.5px",
            background: "linear-gradient(135deg, #fff 40%, #94a3b8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent"
          }}>
            Hiring Data Analytics
          </span>
        </div>

        {/* Dashboard Status */}
        <div className="glass-panel" style={{ padding: "16px", marginBottom: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <Activity size={14} />
              <span>Backend Status</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: backendHealth.status === "healthy" ? "var(--success)" : "var(--error)",
                boxShadow: backendHealth.status === "healthy" ? "0 0 10px var(--success)" : "0 0 10px var(--error)"
              }} />
              <span style={{ fontSize: "0.8rem", fontWeight: 600, color: backendHealth.status === "healthy" ? "#fff" : "var(--error)" }}>
                {backendHealth.status === "healthy" ? "Online" : backendHealth.status === "checking" ? "Checking..." : "Offline"}
              </span>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.85rem", color: "var(--text-muted)" }}>
              <Database size={14} />
              <span>Local Database</span>
            </div>
            <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#fff" }}>
              {backendHealth.database === "connected" ? "Connected" : "Disconnected"}
            </span>
          </div>

          <div style={{
            borderTop: "1px solid var(--panel-border)",
            paddingTop: "10px",
            display: "flex",
            flexDirection: "column",
            gap: "2px"
          }}>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Indexed Candidate Profiles:</span>
            <span style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--primary)" }}>
              {(backendHealth.indexed_candidates || 0).toLocaleString()} candidates
            </span>
          </div>
        </div>

        {/* New Chat Button */}
        <button
          onClick={handleNewChat}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
            background: "var(--gradient-btn)",
            border: "none",
            borderRadius: "12px",
            padding: "12px",
            color: "#fff",
            fontWeight: 600,
            fontSize: "0.9rem",
            cursor: "pointer",
            marginBottom: "20px",
            transition: "all 0.2s ease"
          }}
          onMouseEnter={(e) => e.currentTarget.style.filter = "brightness(1.15)"}
          onMouseLeave={(e) => e.currentTarget.style.filter = "brightness(1)"}
        >
          <Plus size={16} />
          New Chat
        </button>

        {/* Chat Sessions History List */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <h4 style={{
            fontSize: "0.75rem",
            textTransform: "uppercase",
            letterSpacing: "0.5px",
            color: "var(--text-muted)",
            marginBottom: "12px",
            fontWeight: 700
          }}>
            Conversations
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", overflowY: "auto", paddingRight: "4px" }}>
            {chats.map((chat) => {
              const isActive = chat.id === activeChatId;
              return (
                <div
                  key={chat.id}
                  onClick={() => setActiveChatId(chat.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    borderRadius: "10px",
                    cursor: "pointer",
                    background: isActive ? "rgba(139, 92, 246, 0.12)" : "transparent",
                    border: isActive ? "1px solid rgba(139, 92, 246, 0.3)" : "1px solid transparent",
                    transition: "all 0.2s ease",
                    position: "relative"
                  }}
                  className="chat-history-item"
                  onMouseEnter={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)";
                      e.currentTarget.style.borderColor = "var(--panel-border)";
                    }
                    const deleteBtn = e.currentTarget.querySelector(".delete-chat-btn");
                    if (deleteBtn) deleteBtn.style.opacity = 1;
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      e.currentTarget.style.background = "transparent";
                      e.currentTarget.style.borderColor = "transparent";
                    }
                    const deleteBtn = e.currentTarget.querySelector(".delete-chat-btn");
                    if (deleteBtn) deleteBtn.style.opacity = 0;
                  }}
                >
                  <span style={{
                    fontSize: "0.85rem",
                    color: isActive ? "#fff" : "var(--text-muted)",
                    fontWeight: isActive ? 600 : 500,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    maxWidth: "180px"
                  }}>
                    {chat.title}
                  </span>

                  <button
                    className="delete-chat-btn"
                    onClick={(e) => handleDeleteChat(chat.id, e)}
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "var(--text-muted)",
                      cursor: "pointer",
                      padding: "4px",
                      borderRadius: "6px",
                      opacity: 0,
                      transition: "all 0.15s ease",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center"
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = "var(--error)"; e.currentTarget.style.backgroundColor = "rgba(239, 68, 68, 0.1)" }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = "var(--text-muted)"; e.currentTarget.style.backgroundColor = "transparent" }}
                    title="Delete Chat"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer Credit */}
        <div style={{ borderTop: "1px solid var(--panel-border)", paddingTop: "16px", marginTop: "16px", fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "center" }}>
          Hiring Data Analytics v1.0.0
        </div>
      </div>

      {/* Main Chat Area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", padding: "24px" }}>

        {/* Chat Feed Panel */}
        <div className="glass-panel" style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          marginBottom: "20px"
        }}>

          {/* Conversation Screen */}
          <div style={{
            flex: 1,
            overflowY: "auto",
            padding: "24px",
            display: "flex",
            flexDirection: "column",
            gap: "16px"
          }}>
            {messages.length === 0 ? (

              /* Welcome Greeting Screen */
              <div style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                maxWidth: "600px",
                margin: "0 auto",
                textAlign: "center"
              }}>
                <div style={{
                  background: "var(--primary-glow)",
                  padding: "16px",
                  borderRadius: "50%",
                  marginBottom: "20px",
                  border: "1px solid rgba(139, 92, 246, 0.3)",
                  animation: "pulse 3s infinite"
                }}>
                  <Bot size={40} className="text-violet-400" />
                </div>
                <h2 style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "1.7rem", color: "#fff", marginBottom: "12px" }}>
                  AI Assistant
                </h2>
                <p style={{ fontSize: "0.95rem", color: "var(--text-muted)", lineHeight: "1.6", maxWidth: "480px" }}>
                  I can assist you with searching, filtering, and analyzing the candidate database. 
                  The dataset consists of 5,000 candidate profiles from the 2020 to 2025 graduation batches.
                </p>
              </div>
            ) : (

              /* Message Bubbles */
              messages.map((msg, index) => (
                <div
                  key={index}
                  className="animate-slide-up"
                  style={{
                    display: "flex",
                    justifyContent: msg.sender === "user" ? "flex-end" : "flex-start",
                    width: "100%"
                  }}
                >
                  <div style={{
                    display: "flex",
                    gap: "12px",
                    maxWidth: "75%",
                    flexDirection: msg.sender === "user" ? "row-reverse" : "row"
                  }}>
                    {/* Avatar Icon */}
                    <div style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "50%",
                      background: msg.sender === "user" ? "var(--gradient-btn)" : "rgba(255,255,255,0.05)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      border: msg.sender === "bot" ? "1px solid var(--panel-border)" : "none"
                    }}>
                      {msg.sender === "user" ? <User size={16} color="#fff" /> : <Bot size={16} className="text-violet-400" />}
                    </div>

                    {/* Content Bubble */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                      <div className="glass-panel" style={{
                        padding: "14px 18px",
                        borderRadius: "16px",
                        background: msg.sender === "user" ? "var(--gradient-bubble-user)" : "var(--gradient-bubble-bot)",
                        borderColor: msg.sender === "user" ? "rgba(139, 92, 246, 0.2)" : "var(--panel-border)"
                      }}>
                        {msg.sender === "user" ? (
                          <p style={{ fontSize: "0.9rem", color: "#fff", lineHeight: "1.5" }}>{msg.text}</p>
                        ) : (
                          formatResponse(msg.text)
                        )}
                      </div>
                      <span style={{
                        fontSize: "0.7rem",
                        color: "var(--text-muted)",
                        alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
                        padding: "0 4px"
                      }}>
                        {msg.timestamp}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}

            {/* Spinner for Bot thinking */}
            {loading && (
              <div style={{ display: "flex", justifyContent: "flex-start", width: "100%" }}>
                <div style={{ display: "flex", gap: "12px", maxWidth: "75%" }}>
                  <div style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "50%",
                    background: "rgba(255,255,255,0.05)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: "1px solid var(--panel-border)"
                  }}>
                    <Bot size={16} className="text-violet-400" />
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    <div className="glass-panel" style={{
                      padding: "14px 20px",
                      borderRadius: "16px",
                      background: "var(--gradient-bubble-bot)",
                      display: "flex",
                      alignItems: "center",
                      gap: "10px"
                    }}>
                      <div style={{ display: "flex", gap: "4px" }}>
                        <span className="dot" style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "var(--primary)", animation: "pulse 1.2s infinite" }} />
                        <span className="dot" style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "var(--primary)", animation: "pulse 1.2s infinite 0.2s" }} />
                        <span className="dot" style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "var(--primary)", animation: "pulse 1.2s infinite 0.4s" }} />
                      </div>
                      <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Searching database & generating answer...</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        </div>

        {/* Input Form Area */}
        <form onSubmit={handleSend} style={{ display: "flex", gap: "12px", width: "100%" }}>
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={
              backendHealth.status === "healthy"
                ? "Search candidates (e.g. BITS Goa Python candidates with high CGPA)..."
                : "Database disconnected. Please check backend server..."
            }
            disabled={backendHealth.status !== "healthy" || loading}
            style={{
              flex: 1,
              background: "var(--panel-bg)",
              border: "1px solid var(--panel-border)",
              borderRadius: "14px",
              padding: "16px 20px",
              color: "#fff",
              fontSize: "0.95rem",
              outline: "none",
              transition: "all 0.2s ease"
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "var(--panel-border-focus)";
              e.currentTarget.style.boxShadow = "0 0 15px var(--primary-glow)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = "var(--panel-border)";
              e.currentTarget.style.boxShadow = "none";
            }}
          />

          <button
            type="submit"
            disabled={backendHealth.status !== "healthy" || !inputText.trim() || loading}
            style={{
              background: "var(--gradient-btn)",
              border: "none",
              borderRadius: "14px",
              padding: "0 24px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontWeight: 600,
              gap: "8px",
              transition: "transform 0.1s ease, filter 0.2s ease",
              opacity: (backendHealth.status !== "healthy" || !inputText.trim() || loading) ? 0.5 : 1
            }}
            onMouseEnter={(e) => e.currentTarget.style.filter = "brightness(1.15)"}
            onMouseLeave={(e) => e.currentTarget.style.filter = "brightness(1.0)"}
          >
            <span style={{ fontSize: "0.9rem" }}>Send Query</span>
            <Send size={14} />
          </button>
        </form>
      </div>

    </div>
  );
}
