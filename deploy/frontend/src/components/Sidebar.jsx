import { useEffect, useState } from 'react'
import { Wrench, User, Settings, Plus, MessageSquare, HelpCircle } from 'lucide-react'
import { getSessions, getFaq } from '../api/client'
import { getUserId } from '../lib/userId'

function relativeTime(iso) {
  if (!iso) return ''
  const then = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`)
  const secs = Math.floor((Date.now() - then.getTime()) / 1000)
  if (Number.isNaN(secs)) return ''
  if (secs < 60) return 'just now'
  const mins = Math.floor(secs / 60)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

export default function Sidebar({ userType, onNewConversation, onLoadConversation, onSend, onFaqSeedClick }) {
  const isOwner = userType === 'owner'
  const [conversations, setConversations] = useState([])
  const [faq, setFaq] = useState([])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const sessions = await getSessions(getUserId())
        if (!cancelled) setConversations(Array.isArray(sessions) ? sessions : [])
      } catch {
        if (!cancelled) setConversations([])
      }
      try {
        const faqs = await getFaq()
        if (!cancelled) setFaq(Array.isArray(faqs) ? faqs : [])
      } catch {
        if (!cancelled) setFaq([])
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const handleFaqClick = (item) => {
    if (item.source === 'seed') {
      onFaqSeedClick?.(item.question, item.answer, item.citations, item.confidence_score)
    } else {
      onSend?.(item.question)
    }
  }

  return (
    <div className="w-52 border-r border-white/10 flex flex-col bg-[#141414] flex-shrink-0">
      <div className="p-4 border-b border-white/10 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
          <Wrench size={14} color="white" />
        </div>
        <div>
          <div className="text-sm font-medium text-white">MechAI</div>
          <div className="text-[10px] text-white/40">Service Manual Assistant</div>
        </div>
      </div>

      <div className="px-3 pt-4 pb-2">
        <div className="text-[11px] text-white/30 uppercase tracking-wide mb-2">Current Mode</div>
        <div className="flex items-center gap-2 px-3 py-2 bg-blue-600/20 border border-blue-500/20 rounded-lg">
          {isOwner
            ? <User size={14} className="text-blue-400" />
            : <Settings size={14} className="text-blue-400" />}
          <span className="text-sm text-blue-300 font-medium capitalize">{userType}</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {conversations.length > 0 && (
          <div className="px-3 pt-3 pb-2">
            <div className="text-[11px] text-white/30 uppercase tracking-wide mb-2 flex items-center gap-1">
              <MessageSquare size={11} /> Recent Conversations
            </div>
            <div className="flex flex-col gap-1">
              {conversations.map((c) => (
                <button
                  key={c.session_id}
                  onClick={() => onLoadConversation?.(c.session_id, c.user_type)}
                  className="text-left px-2.5 py-1.5 rounded-lg hover:bg-white/5 transition-colors"
                >
                  <div className="text-xs text-white/70 truncate">{c.preview || 'Untitled conversation'}</div>
                  <div className="text-[10px] text-white/30">{relativeTime(c.timestamp)}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {faq.length > 0 && (
          <div className="px-3 pt-3 pb-2">
            <div className="text-[11px] text-white/30 uppercase tracking-wide mb-2 flex items-center gap-1">
              <HelpCircle size={11} /> Frequently Asked
            </div>
            <div className="flex flex-col gap-1">
              {faq.map((item, i) => (
                <button
                  key={i}
                  onClick={() => handleFaqClick(item)}
                  className="text-left px-2.5 py-1.5 rounded-lg hover:bg-white/5 transition-colors text-xs text-white/60"
                >
                  {item.question}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="p-3">
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
