import clsx from "clsx"

interface BadgeProps {
  readonly children: React.ReactNode
  readonly variant?: "accent" | "gray"
  readonly size?: "sm" | "md"
}

export default function Badge({ children, variant = "gray", size = "sm" }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full font-medium",
        size === "sm" && "px-2 py-0.5 text-[10px] uppercase tracking-wider",
        size === "md" && "px-3 py-1 text-xs",
        variant === "accent" && "border border-accent/30 bg-accent/10 text-accent",
        variant === "gray" && "border border-white/20 bg-white/5 text-gray-400"
      )}
    >
      {children}
    </span>
  )
}
