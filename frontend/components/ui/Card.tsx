import { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-card border border-line bg-panel p-6 shadow-panel ${className}`}
    >
      {children}
    </div>
  );
}
