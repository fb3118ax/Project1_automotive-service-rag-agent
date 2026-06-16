import { User, Settings } from 'lucide-react'

export default function ModeSelect({ onSelect }) {
  return (
    <div className="h-screen flex flex-col items-center justify-center bg-[#0f0f0f]">
      <div className="mb-10 text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
          </div>
          <span className="text-xl font-semibold text-white">MechAI</span>
        </div>
        <p className="text-sm text-white/40">Service Manual Assistant</p>
      </div>

      <p className="text-white/60 text-sm mb-6">Select your user type to continue</p>

      <div className="flex gap-4">
        <button
          onClick={() => onSelect('owner')}
          className="flex flex-col items-center gap-3 w-44 px-6 py-8 bg-[#1a1a1a] border border-white/10 rounded-2xl hover:border-blue-500/50 hover:bg-[#1e1e1e] transition-all group"
        >
          <div className="w-12 h-12 rounded-xl bg-blue-600/20 flex items-center justify-center group-hover:bg-blue-600/30 transition-colors">
            <User size={22} className="text-blue-400" />
          </div>
          <div className="text-center">
            <div className="text-sm font-medium text-white">Owner</div>
            <div className="text-[11px] text-white/30 mt-1">Simple guidance &amp; tips</div>
          </div>
        </button>

        <button
          onClick={() => onSelect('technician')}
          className="flex flex-col items-center gap-3 w-44 px-6 py-8 bg-[#1a1a1a] border border-white/10 rounded-2xl hover:border-blue-500/50 hover:bg-[#1e1e1e] transition-all group"
        >
          <div className="w-12 h-12 rounded-xl bg-blue-600/20 flex items-center justify-center group-hover:bg-blue-600/30 transition-colors">
            <Settings size={22} className="text-blue-400" />
          </div>
          <div className="text-center">
            <div className="text-sm font-medium text-white">Technician</div>
            <div className="text-[11px] text-white/30 mt-1">Technical specs &amp; data</div>
          </div>
        </button>
      </div>
    </div>
  )
}
