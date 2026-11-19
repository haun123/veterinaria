import { useState } from 'react'
import BotCard from './components/botCard'
import Connection from './components/conecction'
import DbCard from './components/dbCard'

export default function App() {
  const [active, setActive] = useState([false, false, false])

  const toggle = (index: number) =>
    setActive((prev) => prev.map((v, i) => (i === index ? !v : v)))

  return (
    <main className="flex min-h-screen items-center justify-center gap-6 bg-zinc-950 p-8 text-zinc-100">
      <div className="flex flex-col gap-6">
        {active.map((isActive, i) => (
          <BotCard
            key={i}
            name={`Bot ${i + 1}`}
            active={isActive}
            onToggle={() => toggle(i)}
          />
        ))}
      </div>

      <Connection status="error" />
      <DbCard name="Base de datos" active={false} />
      <Connection status="error" />
      <DbCard name="DB 2" active={false} circle />
    </main>
  )
}