"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { ListingCard } from "./listing-card";
import { useResearchStore } from "@/stores/research-store";
import type { Listing, PipelineStage } from "@/types";

interface PipelineColumnProps {
  stage: { key: PipelineStage; label: string; color: string };
  listings: Listing[];
  campaignId: string;
}

export function PipelineColumn({
  stage,
  listings,
  campaignId,
}: PipelineColumnProps) {
  const { selectedIds, selectAll, clearSelection } = useResearchStore();
  const isNewColumn = stage.key === "new";
  const allSelected =
    isNewColumn &&
    listings.length > 0 &&
    listings.every((l) => selectedIds.has(l.id));

  const handleSelectAll = () => {
    if (allSelected) {
      clearSelection();
    } else {
      selectAll(listings.map((l) => l.id));
    }
  };

  return (
    <div className="flex flex-col min-w-[280px] w-[280px] h-full bg-muted/30 rounded-lg overflow-hidden">
      {/* Column header - fixed */}
      <div className="flex-shrink-0 flex items-center justify-between px-3 py-2.5 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          {isNewColumn && listings.length > 0 && (
            <Checkbox
              checked={allSelected}
              onCheckedChange={handleSelectAll}
              className="mr-0.5"
            />
          )}
          <div className={`w-2 h-2 rounded-full ${stage.color}`} />
          <span className="text-sm font-medium">{stage.label}</span>
        </div>
        <Badge variant="secondary" className="text-xs h-5 px-1.5">
          {listings.length}
        </Badge>
      </div>

      {/* Cards - scrollable */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-2 space-y-2">
          {listings.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-8">
              Chưa có tin nào
            </p>
          ) : (
            listings.map((listing) => (
              <ListingCard
                key={listing.id}
                listing={listing}
                campaignId={campaignId}
                selectable={isNewColumn}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
