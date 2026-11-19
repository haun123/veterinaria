import { useState } from 'react'
import { Bot, BarChart3, Play, Square, Send, CheckCircle2, XCircle } from 'lucide-react'
import Modal from './modal'
import StatCard from './statCard'

type BotCardProps = {
  name: string
  active: boolean
  onToggle: () => void
}

export default function BotCard({ name, active, onToggle }: BotCardProps) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <div
        className={`flex h-44 w-60 flex-col justify-between rounded-2xl border bg-zinc-900 p-4 transition-colors ${
          active ? 'border-green-500/50' : 'border-zinc-800'
        }`}
      >
        <div className="flex items-center justify-between">
          <span
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
              active ? 'bg-green-500/15 text-green-400' : 'bg-zinc-800 text-zinc-400'
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-green-400' : 'bg-zinc-500'}`}
            />
            {active ? 'Activo' : 'Inactivo'}
          </span>

          <button
            onClick={() => setOpen(true)}
            aria-label={`Ver detalles de ${name}`}
            className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-white"
          >
            <BarChart3 size={18} />
          </button>
        </div>

        <div className="flex items-center justify-center gap-2">
          <Bot size={28} className={active ? 'text-green-400' : 'text-zinc-500'} />
          <p className="text-lg font-semibold">{name}</p>
        </div>

        <button
          onClick={onToggle}
          className={`flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            active
              ? 'bg-red-500/15 text-red-400 hover:bg-red-500/25'
              : 'bg-green-500 text-zinc-950 hover:bg-green-400'
          }`}
        >
          {active ? <Square size={16} /> : <Play size={16} />}
          {active ? 'Detener' : 'Iniciar'}
        </button>
      </div>

      {open && (
        <Modal title={`${name} · Detalles`} onClose={() => setOpen(false)}>
          <div className="grid grid-cols-3 gap-3">
            <StatCard label="Enviados" icon={Send} color="text-blue-400" />
            <StatCard label="Exitosos" icon={CheckCircle2} color="text-green-400" />
            <StatCard label="Fallidos" icon={XCircle} color="text-red-400" />
          </div>
        </Modal>
      )}
    </>
  )
}