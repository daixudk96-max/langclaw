"use client";

import { useCampaignStore } from "@/stores/campaign-store";

export function StatsPanel() {
  const { stats } = useCampaignStore();

  if (!stats) return null;

  const items = [
    { label: "Total", value: stats.total_listings },
    { label: "New today", value: stats.new_today },
    { label: "Scans", value: stats.total_scans },
    { label: "Selected", value: stats.by_stage?.shortlisted || 0 },
  ];

  return (
    <div className="flex items-center gap-4">
      {items.map((item) => (
        <div key={item.label} className="text-center">
          <p className="text-xl font-semibold tabular-nums">{item.value}</p>
          <p className="text-xs text-muted-foreground">{item.label}</p>
        </div>
      ))}
    </div>
  );
}
