import { useState } from 'react'
import { FileText, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'

function ConfidenceBadge({ score }) {
  if (score === null) return null
  if (score < 0.4) return <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-900/50 text-green-400 font-medium">High confidence</span>
  if (score <= 0.7) return <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-900/50 text-amber-400 font-medium">Acceptable confidence</span>
  return <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-900/50 text-red-400 font-medium">Low confidence</span>
}

export default function MessageBubble({ message }) {
  const [citationsOpen, setCitationsOpen] = useState(false)
  const { role, content, confidence_score, citations, guardrail, error } = message

  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-blue-600 text-white text-sm px-4 py-2.5 rounded-2xl rounded-br-sm leading-relaxed">
          {content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-start max-w-[80%]">
      {guardrail ? (
        <div className="bg-amber-900/30 border border-amber-700/40 text-amber-400 text-sm px-4 py-2.5 rounded-2xl rounded-bl-sm leading-relaxed flex items-start gap-2">
          <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
          {content}
        </div>
      ) : (
        <div className={`bg-[#1e1e1e] text-white/90 text-sm px-4 py-2.5 rounded-2xl rounded-bl-sm leading-relaxed border border-white/10 ${error ? 'text-red-400' : ''}`}>
          {content}
        </div>
      )}

      {!guardrail && !error && (
        <div className="flex items-center gap-2 mt-1.5">
          <ConfidenceBadge score={confidence_score} />

          {citations && citations.length > 0 && (
            <button
              onClick={() => setCitationsOpen(o => !o)}
              className="flex items-center gap-1 text-[11px] text-white/30 hover:text-white/60 transition-colors"
            >
              <FileText size={11} />
              {citations.length === 1
                ? `Page ${citations[0].page}`
                : `Pages ${citations.map(c => c.page).join(', ')}`}
              {citationsOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>
          )}

          {guardrail && (
            <span className="text-[11px] text-white/30">Guardrail triggered</span>
          )}
        </div>
      )}

      {citationsOpen && citations?.length > 0 && (
        <div className="mt-1.5 px-3 py-2 bg-[#1a1a1a] border border-white/10 rounded-lg text-[11px] text-white/40 leading-loose">
          {citations.map((c, i) => (
            <div key={i}>Page {c.page} · {c.source}</div>
          ))}
        </div>
      )}
    </div>
  )
}
