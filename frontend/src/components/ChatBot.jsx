/**
 * ChatBot UI — displays Q&A conversation history and input box.
 * Supports markdown rendering and animated typing indicator.
 */
import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { Send, Bot, User, Loader2, ChevronDown, BookOpen } from 'lucide-react'
import api from '../services/api'

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2 animate-fade-in">
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shrink-0">
        <Bot size={14} className="text-white" />
      </div>
      <div className="chat-bubble-ai px-4 py-3 flex gap-1.5 items-center">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  )
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  const [showSources, setShowSources] = useState(false)

  return (
    <div className={`flex items-end gap-2 animate-slide-up ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0
                      ${isUser
                        ? 'bg-gradient-to-br from-slate-600 to-slate-700'
                        : 'bg-gradient-to-br from-brand-500 to-purple-600'}`}>
        {isUser ? <User size={14} className="text-white" /> : <Bot size={14} className="text-white" />}
      </div>

      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        {/* Bubble */}
        <div className={`px-4 py-3 text-sm leading-relaxed ${isUser ? 'chat-bubble-user text-white' : 'chat-bubble-ai text-slate-200'}`}>
          {isUser ? (
            <p>{msg.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Source chunks (AI only) */}
        {!isUser && msg.sources?.length > 0 && (
          <button
            onClick={() => setShowSources(!showSources)}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-brand-400 transition-colors ml-1"
          >
            <BookOpen size={11} />
            {msg.sources.length} source{msg.sources.length > 1 ? 's' : ''}
            <ChevronDown size={11} className={`transition-transform ${showSources ? 'rotate-180' : ''}`} />
          </button>
        )}
        {showSources && (
          <div className="ml-1 space-y-1 w-full">
            {msg.sources.map((src, i) => (
              <div key={i} className="bg-surface-50 border border-white/10 rounded-lg p-2.5 text-xs text-slate-400 font-mono leading-relaxed">
                <span className="text-brand-400 font-semibold">Score: {src.score.toFixed(2)}</span>
                <p className="mt-1 line-clamp-3">{src.text}</p>
              </div>
            ))}
          </div>
        )}

        <span className="text-xs text-slate-600 mx-1">
          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  )
}

export default function ChatBot({ documentId, documentName }) {
  const getWelcomeMessage = (name) => ({
    role: 'ai',
    content: name
      ? `Hi! I've loaded **${name}**. Ask me anything about it!`
      : `Select a document from the sidebar to start asking questions.`,
    timestamp: Date.now(),
    sources: [],
  })

  const [messages, setMessages] = useState([getWelcomeMessage(documentName)])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  // Reset chat when document changes
  useEffect(() => {
    setMessages([getWelcomeMessage(documentName)])
    setInput('')
  }, [documentId])

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading || !documentId) return

    const question = input.trim()
    setInput('')

    // Append user message
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: question, timestamp: Date.now() },
    ])

    setLoading(true)
    try {
      const { data } = await api.post(`/qa/${documentId}/ask`, { question })
      setMessages((prev) => [
        ...prev,
        {
          role: 'ai',
          content: data.answer,
          sources: data.source_chunks,
          timestamp: Date.now(),
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'ai',
          content: `⚠️ ${err.response?.data?.detail || 'Something went wrong. Please try again.'}`,
          timestamp: Date.now(),
          sources: [],
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10 flex items-center gap-2 shrink-0">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center">
          <Bot size={16} className="text-white" />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-200">AI Assistant</p>
          <p className="text-xs text-slate-500 truncate max-w-48">{documentName || 'Select a document'}</p>
        </div>
        {!documentId && (
          <span className="ml-auto text-xs text-amber-400 bg-amber-400/10 px-2 py-1 rounded-full">
            No document selected
          </span>
        )}
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={sendMessage} className="p-4 border-t border-white/10 shrink-0">
        <div className="flex gap-2">
          <input
            id="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={documentId ? 'Ask a question…' : 'Select a document first…'}
            disabled={!documentId || loading}
            className="flex-1 bg-surface-50 border border-white/10 rounded-xl px-4 py-3 text-sm text-slate-100
                       placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-brand-500
                       disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          />
          <button
            id="btn-send-chat"
            type="submit"
            disabled={!input.trim() || !documentId || loading}
            className="w-12 h-12 bg-gradient-to-br from-brand-600 to-purple-600 rounded-xl
                       flex items-center justify-center hover:from-brand-500 hover:to-purple-500
                       transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed
                       hover:shadow-lg hover:shadow-brand-500/30"
          >
            {loading ? <Loader2 size={18} className="text-white animate-spin" /> : <Send size={18} className="text-white" />}
          </button>
        </div>
      </form>
    </div>
  )
}
