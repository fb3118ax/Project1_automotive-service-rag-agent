import { useState } from 'react'
import { Star } from 'lucide-react'

export default function FeedbackModal({ onSubmit, onDismiss }) {
  const [rating, setRating] = useState(0)
  const [hoverRating, setHoverRating] = useState(0)
  const [comment, setComment] = useState('')

  const handleSubmit = () => {
    if (rating === 0) return
    onSubmit(rating, comment)
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 px-4">
      <div className="bg-[#171717] border border-white/10 rounded-xl p-6 w-full max-w-sm">
        <h2 className="text-sm font-medium text-white/80 mb-1">How's it going so far?</h2>
        <p className="text-xs text-white/40 mb-4">Your feedback helps us improve MechAI.</p>

        <div className="flex gap-1 mb-4">
          {[1, 2, 3, 4, 5].map(n => (
            <button
              key={n}
              type="button"
              onClick={() => setRating(n)}
              onMouseEnter={() => setHoverRating(n)}
              onMouseLeave={() => setHoverRating(0)}
            >
              <Star
                size={24}
                className={n <= (hoverRating || rating) ? 'fill-yellow-400 text-yellow-400' : 'text-white/20'}
              />
            </button>
          ))}
        </div>

        <textarea
          value={comment}
          onChange={e => setComment(e.target.value)}
          placeholder="Any comments? (optional)"
          rows={3}
          className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 placeholder-white/20 resize-none focus:outline-none focus:border-white/30"
        />

        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={onDismiss}
            className="text-xs text-white/40 px-3 py-2 hover:text-white/60"
          >
            Skip
          </button>
          <button
            onClick={handleSubmit}
            disabled={rating === 0}
            className="text-xs bg-white/90 text-black px-4 py-2 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  )
}