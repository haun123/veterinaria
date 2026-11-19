import type { LucideIcon } from 'lucide-react'

type StatCardProps = {
  label: string
  icon: LucideIcon
  color: string
}

export default function StatCard({ label, icon: Icon, color }: StatCardProps) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-xl border border-zinc-800 bg-zinc-950 p-4">
      <Icon size={20} className={color} />
      <span className="text-2xl font-bold text-zinc-600">—</span>
      <span className="text-xs text-zinc-400">{label}</span>
    </div>
  )
}