type ConnectionProps = {
  status: 'ok' | 'error'
}

export default function Connection({ status }: ConnectionProps) {
  const color = status === 'ok' ? 'bg-green-500' : 'bg-red-500'

  return (
    <div className="flex items-center gap-1">
      {[0, 1, 2, 3, 4].map((i) => (
        <span key={i} className={`h-3 w-5 rounded-full ${color}`} />
      ))}
    </div>
  )
}