import { useState } from 'react'
import { Database, BarChart3, Download, CheckCircle2, XCircle } from 'lucide-react'
import Modal from './modal'
import StatCard from './statCard'

type DbCardProps = {
  name: string
  active: boolean
  circle?: boolean
}

export default function DbCard({ name, active, circle = false }: DbCardProps) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <div
        className={`flex flex-col items-center justify-center gap-1.5 border bg-zinc-900 p-4 transition-colors ${
          circle ? 'h-48 w-48 rounded-full' : 'h-44 w-52 rounded-2xl'
        } ${active ? 'border-green-500/50' : 'border-zinc-800'}`}
      >
        <Database size={26} className={active ? 'text-green-400' : 'text-zinc-500'} />
        <p className="font-semibold">{name}</p>

        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
            active ? 'bg-green-500/15 text-green-400' : 'bg-zinc-800 text-zinc-400'
          }`}
        >
          {active ? 'Activa' : 'Inactiva'}
        </span>

        <button
          onClick={() => setOpen(true)}
          className="mt-1 flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-zinc-400 hover:bg-zinc-800 hover:text-white"
        >
          <BarChart3 size={14} />
          Detalles
        </button>
      </div>

      {open && (
        <Modal title={`${name} · Detalles`} onClose={() => setOpen(false)}>
          <div className="grid grid-cols-3 gap-3">
            <StatCard label="Recibidos" icon={Download} color="text-blue-400" />
            <StatCard label="Agregados" icon={CheckCircle2} color="text-green-400" />
            <StatCard label="Fallidos" icon={XCircle} color="text-red-400" />
          </div>
        </Modal>
      )}
    </>
  )
}