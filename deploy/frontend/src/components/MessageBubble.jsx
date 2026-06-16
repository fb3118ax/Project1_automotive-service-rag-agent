import { useState } from 'react'
import { FileText, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'

function ConfidenceBadge({ score }) {
  if (score === null) return null
  if (score < 0.4) return <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-100 text-green-800 font-medium">High confidence</span>
  if (score <= 0.7) return <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-medium">Acceptable confidence</span>
  return <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 text-red-800 font-medium">Low confidence</span>
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
        <div className="bg-amber-50 border border-amber-200 text-amber-800 text-sm px-4 py-2.5 rounded-2xl rounded-bl-sm leading-relaxed flex items-start gap-2">
          <AlertTriangle size={14} className="mt-0.5 flex-shrink-0" />
          {content}
        </div>
      ) : (
        <div className={`bg-gray-100 text-gray-900 text-sm px-4 py-2.5 rounded-2xl rounded-bl-sm leading-relaxed border border-gray-200 ${error ? 'text-red-600' : ''}`}>
          {content}
        </div>
      )}

      {!guardrail && !error && (
        <div className="flex items-center gap-2 mt-1.5">
          <ConfidenceBadge score={confidence_score} />

          {citations && citations.length > 0 && (
            <button
              onClick={() => setCitationsOpen(o => !o)}
              className="flex items-center gap-1 text-[11px] text-gray-400 hover:text-gray-600 transition-colors"
            >
              <FileText size={11} />
              {citations.length === 1
                ? `Page ${citations[0].page}`
                : `Pages ${citations.map(c => c.page).join(', ')}`}
              {citationsOpen ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            </button>
          )}

          {guardrail && (
            <span className="text-[11px] text-gray-400">Guardrail triggered</span>
          )}
        </div>
      )}

      {citationsOpen && citations?.length > 0 && (
        <div className="mt-1.5 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-[11px] text-gray-500 leading-loose">
          {citations.map((c, i) => (
            <div key={i}>Page {c.page} · {c.source}</div>
          ))}
        </div>
      )}
    </div>
  )
}
