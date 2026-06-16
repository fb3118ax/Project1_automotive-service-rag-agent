import { Wrench, User, Settings, Plus } from 'lucide-react'

export default function Sidebar({ userType, onModeSwitch, onNewConversation }) {
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

      <div className="px-3 pt-3 pb-1 text-[11px] text-white/30 uppercase tracking-wide">
        User Mode
      </div>

      <button
        onClick={() => onModeSwitch('owner')}
        className={`flex items-center gap-2 px-4 py-2 text-sm w-full text-left transition-colors
          ${userType === 'owner'
            ? 'bg-blue-600 text-white font-medium'
            : 'text-white/50 hover:bg-white/5'}`}
      >
        <User size={15} />
        Owner
      </button>

      <button
        onClick={() => onModeSwitch('technician')}
        className={`flex items-center gap-2 px-4 py-2 text-sm w-full text-left transition-colors
          ${userType === 'technician'
            ? 'bg-blue-600 text-white font-medium'
            : 'text-white/50 hover:bg-white/5'}`}
      >
        <Settings size={15} />
        Technician
      </button>

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
