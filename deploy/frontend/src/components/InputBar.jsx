import { useState, useRef } from 'react'
import { Send } from 'lucide-react'

const MAX_CHARS = 500

export default function InputBar({ onSend, disabled }) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) textareaRef.current.style.height = '38px'
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleChange = (e) => {
    const val = e.target.value
    if (val.length > MAX_CHARS) return
    setValue(val)
    e.target.style.height = '38px'
    e.target.style.height = `${e.target.scrollHeight}px`
  }

  const remaining = MAX_CHARS - value.length
  const nearLimit = remaining <= 50

  return (
    <div className="border-t border-white/10 px-4 pt-3 pb-4 bg-[#0f0f0f]">
      <div className="flex gap-2 items-end">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask about your vehicle…"
          rows={1}
          className="flex-1 resize-none border border-white/10 rounded-xl px-3 py-2 text-sm text-white/90 placeholder-white/20 focus:outline-none focus:border-blue-500/50 disabled:opacity-50 bg-[#1a1a1a] overflow-hidden"
          style={{ minHeight: '38px', maxHeight: '120px' }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center flex-shrink-0 hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          aria-label="Send"
        >
          <Send size={15} color="white" />
        </button>
      </div>
      <div className={`text-right text-[10px] mt-1 ${nearLimit ? 'text-amber-500' : 'text-white/20'}`}>
        {remaining} / {MAX_CHARS}
      </div>
    </div>
  )
}
