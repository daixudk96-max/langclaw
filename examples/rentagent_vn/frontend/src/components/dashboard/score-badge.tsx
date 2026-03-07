"use client";

import { cn } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  className?: string;
}

function getScoreColor(score: number): string {
  if (score >= 8) return "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (score >= 6) return "bg-green-100 text-green-700 border-green-200";
  if (score >= 4) return "bg-orange-100 text-orange-700 border-orange-200";
  return "bg-red-100 text-red-700 border-red-200";
}

const SIZE_CLASSES = {
  sm: "text-[10px] px-1 py-0.5 min-w-[32px]",
  md: "text-xs px-1.5 py-0.5 min-w-[40px]",
  lg: "text-sm px-2 py-1 min-w-[48px]",
};

export function ScoreBadge({ score, size = "md", className }: ScoreBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center rounded-md border font-semibold tabular-nums",
        getScoreColor(score),
        SIZE_CLASSES[size],
        className
      )}
    >
      {score.toFixed(1)}
    </span>
  );
}
