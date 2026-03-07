"use client";

import { cn } from "@/lib/utils";
import type { ResearchScores } from "@/types";

interface CriteriaScoresProps {
  scores: ResearchScores;
  compact?: boolean;
}

function getBarColor(score: number): string {
  if (score >= 8) return "bg-emerald-500";
  if (score >= 6) return "bg-green-500";
  if (score >= 4) return "bg-orange-500";
  return "bg-red-500";
}

export function CriteriaScores({ scores, compact }: CriteriaScoresProps) {
  return (
    <div
      className={cn(
        "grid gap-2",
        compact ? "grid-cols-1" : "grid-cols-1 sm:grid-cols-2"
      )}
    >
      {scores.criteria.map((criterion) => (
        <div key={criterion.criterion_key} className="space-y-1">
          <div className="flex items-center justify-between">
            <span
              className={cn(
                "text-muted-foreground truncate",
                compact ? "text-[11px]" : "text-xs"
              )}
            >
              {criterion.label}
            </span>
            <span
              className={cn(
                "font-semibold tabular-nums",
                compact ? "text-[11px]" : "text-xs"
              )}
            >
              {criterion.score}/10
            </span>
          </div>
          <div
            className={cn(
              "w-full rounded-full bg-muted",
              compact ? "h-1" : "h-1.5"
            )}
          >
            <div
              className={cn(
                "rounded-full transition-all",
                compact ? "h-1" : "h-1.5",
                getBarColor(criterion.score)
              )}
              style={{ width: `${criterion.score * 10}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
