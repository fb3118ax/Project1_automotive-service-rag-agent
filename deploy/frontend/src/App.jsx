import { useEffect, useRef } from 'react'
import { Clock } from 'lucide-react'
import { useChat } from './hooks/useChat'
import Sidebar from './components/Sidebar'
import MessageBubble from './components/MessageBubble'
import InputBar from './components/InputBar'

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-1">
      {[0, 150, 300].map(delay => (
        <span
          key={delay}
          className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
      <span className="text-xs text-gray-400 ml-1">Agent is thinking…</span>
    </div>
  )
}

function SlowServerWarning() {
  return (
    <div className="flex items-center gap-1.5 text-[11px] text-gray-400">
      <Clock size={11} />
      Waking up server, this may take 30–60s…
    </div>
  )
}

export default function App() {
  const { messages, loading, slowServer, userType, setUserType, send, newConversation } = useChat()
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  return (
    <div className="h-screen flex bg-white overflow-hidden">
      <Sidebar
        userType={userType}
        setUserType={setUserType}
        onNewConversation={newConversation}
      />

      <div className="flex flex-col flex-1 min-w-0">
        <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between">
          <span className="text-sm font-medium text-gray-900">Service Manual Q&A</span>
          <span className="text-xs text-gray-400 capitalize">{userType} mode · max 500 chars</span>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-3">
          {messages.length === 0 && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-gray-400">
                <p className="text-sm">Ask anything about your vehicle.</p>
                <p className="text-xs mt-1">Responses are grounded in the service manual.</p>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}

          {loading && (
            <div className="flex flex-col gap-1.5">
              <TypingIndicator />
              {slowServer && <SlowServerWarning />}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <InputBar onSend={send} disabled={loading} />
      </div>
    </div>
  )
}
