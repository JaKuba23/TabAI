import clsx from "clsx"

interface CardProps {
  readonly children: React.ReactNode
  readonly highlighted?: boolean
  readonly className?: string
}

export default function Card({ children, highlighted = false, className }: CardProps) {
  return (
    <div
      className={clsx(
        "rounded-2xl border p-6 transition-shadow",
        highlighted
          ? "border-accent/40 bg-accent/[0.04] shadow-lg shadow-accent/5"
          : "border-white/10 bg-white/[0.02]",
        className
      )}
    >
      {children}
    </div>
  )
}
