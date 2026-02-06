import { PropsWithChildren } from "react";
import { cn } from "../../lib/utils";

export function Card({ children, className }: PropsWithChildren<{ className?: string }>) {
  return <div className={cn("rounded-lg bg-slate-900 p-4 shadow", className)}>{children}</div>;
}
