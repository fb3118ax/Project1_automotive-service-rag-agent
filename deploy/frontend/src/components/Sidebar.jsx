import { useEffect, useState } from 'react'
import { Wrench, User, Settings, Plus, History, HelpCircle } from 'lucide-react'
import { getSessions, getFaq } from '../api/client'

function timeAgo(isoString) {
  if (!isoString) return ''
  const diffMs = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

export default function Sidebar({ userType, userId, onNewConversation, onLoadConversation, onSend, onFaqSeedClick }) {
  const isOwner = userType === 'owner'
  const [sessions, setSessions] = useState([])
  const [faq, setFaq] = useState([])

  useEffect(() => {
    if (!userId) return
    getSessions(userId).then(setSessions).catch(() => setSessions([]))
    getFaq().then(setFaq).catch(() => setFaq([]))
  }, [userId])

  const handleFaqClick = (item) => {
    if (item.source === 'seed') {
      onFaqSeedClick(item.question, item.answer, item.citations, item.confidence_score)
    } else {
      onSend(item.question)
    }
  }

  return (
    <div className="w-64 border-r border-white/10 flex flex-col bg-[#141414] flex-shrink-0 overflow-y-auto">
      <div className="p-4 border-b border-white/10 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
          <Wrench size={14} color="white" />
        </div>
        <div>
          <div className="text-sm font-medium text-white">MechAI</div>
          <div className="text-[10px] text-white/40">Service Manual Assistant</div>
        </div>
      </div>

      {userType && (
        <div className="px-3 pt-4 pb-2">
          <div className="text-[11px] text-white/30 uppercase tracking-wide mb-2">Current Mode</div>
          <div className="flex items-center gap-2 px-3 py-2 bg-blue-600/20 border border-blue-500/20 rounded-lg">
            {isOwner
              ? <User size={14} className="text-blue-400" />
              : <Settings size={14} className="text-blue-400" />}
            <span className="text-sm text-blue-300 font-medium capitalize">{userType}</span>
          </div>
        </div>
      )}

      {sessions.length > 0 && (
        <div className="px-3 pt-4 pb-2">
          <div className="flex items-center gap-1.5 text-[11px] text-white/30 uppercase tracking-wide mb-2">
            <History size={11} />
            Recent Conversations
          </div>
          <div className="flex flex-col gap-1">
            {sessions.slice(0, 5).map((s) => (
              <button
                key={s.session_id}
                onClick={() => onLoadConversation(s.session_id, s.user_type)}
                className="text-left px-3 py-2 rounded-lg text-xs text-white/60 hover:bg-white/5 hover:text-white/90 transition-colors border border-transparent hover:border-white/10"
              >
                <div className="truncate">{s.preview || '(no preview)'}</div>
                <div className="text-[10px] text-white/25 mt-0.5">{timeAgo(s.timestamp)} · {s.user_type}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {faq.length > 0 && (
        <div className="px-3 pt-4 pb-2">
          <div className="flex items-center gap-1.5 text-[11px] text-white/30 uppercase tracking-wide mb-2">
            <HelpCircle size={11} />
            Frequently Asked
          </div>
          <div className="flex flex-col gap-1">
            {faq.map((item, i) => (
              <button
                key={i}
                onClick={() => handleFaqClick(item)}
                className="text-left px-3 py-2 rounded-lg text-xs text-white/60 hover:bg-white/5 hover:text-white/90 transition-colors border border-transparent hover:border-white/10"
              >
                {item.question}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="mt-auto p-3">
        <button
          onClick={onNewConversation}
          className="flex items-center gap-2 w-full px-3 py-2 text-xs text-white/40 border border-white/10 rounded-lg hover:bg-white/5 transition-colors"
        >
          <Plus size={13} />
          New conversation
        </button>
      </div>
    </div>
  )
}
