import { Wrench, User, Settings, Plus } from 'lucide-react'

export default function Sidebar({ userType, onNewConversation }) {
  const isOwner = userType === 'owner'

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
