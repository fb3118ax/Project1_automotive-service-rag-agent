import { Wrench, User, Settings, Plus } from 'lucide-react'

export default function Sidebar({ userType, setUserType, onNewConversation }) {
  return (
    <div className="w-52 border-r border-gray-200 flex flex-col bg-gray-50 flex-shrink-0">
      <div className="p-4 border-b border-gray-200 flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
          <Wrench size={14} color="white" />
        </div>
        <div>
          <div className="text-sm font-medium text-gray-900">MechAI</div>
          <div className="text-[10px] text-gray-400">Service Manual Assistant</div>
        </div>
      </div>

      <div className="px-3 pt-3 pb-1 text-[11px] text-gray-400 uppercase tracking-wide">
        User Mode
      </div>

      <button
        onClick={() => setUserType('owner')}
        className={`flex items-center gap-2 px-4 py-2 text-sm w-full text-left transition-colors
          ${userType === 'owner'
            ? 'bg-blue-600 text-white font-medium'
            : 'text-gray-500 hover:bg-gray-100'}`}
      >
        <User size={15} />
        Owner
      </button>

      <button
        onClick={() => setUserType('technician')}
        className={`flex items-center gap-2 px-4 py-2 text-sm w-full text-left transition-colors
          ${userType === 'technician'
            ? 'bg-blue-600 text-white font-medium'
            : 'text-gray-500 hover:bg-gray-100'}`}
      >
        <Settings size={15} />
        Technician
      </button>

      <div className="mt-auto p-3">
        <button
          onClick={onNewConversation}
          className="flex items-center gap-2 w-full px-3 py-2 text-xs text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <Plus size={13} />
          New conversation
        </button>
      </div>
    </div>
  )
}
