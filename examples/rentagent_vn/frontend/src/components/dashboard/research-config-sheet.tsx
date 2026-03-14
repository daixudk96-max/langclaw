"use client";

import { MapPin } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { useResearchStore } from "@/stores/research-store";
import { useListingStore } from "@/stores/listing-store";

interface ResearchConfigSheetProps {
  campaignId: string;
}

export function ResearchConfigSheet({ campaignId }: ResearchConfigSheetProps) {
  const {
    configSheetOpen,
    setConfigSheetOpen,
    selectedIds,
    criteria,
    setCriteria,
    startResearch,
    loading,
  } = useResearchStore();
  const { fetchListings } = useListingStore();

  const enabledCount = criteria.filter((c) => c.enabled).length;

  const handleToggle = (key: string) => {
    setCriteria(
      criteria.map((c) =>
        c.key === key ? { ...c, enabled: !c.enabled } : c
      )
    );
  };

  const handleStart = async () => {
    await startResearch(campaignId, Array.from(selectedIds));
    await fetchListings(campaignId);
  };

  return (
    <Sheet open={configSheetOpen} onOpenChange={setConfigSheetOpen}>
      <SheetContent side="bottom" className="max-h-[80vh]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <MapPin className="h-5 w-5 text-teal-500" />
            Area Research
          </SheetTitle>
          <SheetDescription>
            Select evaluation criteria for {selectedIds.size} listings
          </SheetDescription>
        </SheetHeader>

        <div className="mt-4 space-y-4 overflow-y-auto max-h-[50vh]">
          {/* Criteria checkboxes */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium">Evaluation criteria</p>
              <Badge variant="secondary" className="text-xs">
                {enabledCount}/{criteria.length}
              </Badge>
            </div>
            <div className="space-y-2">
              {criteria.map((c) => (
                <label
                  key={c.key}
                  className="flex items-start gap-3 p-2 rounded-md hover:bg-muted/50 cursor-pointer"
                >
                  <Checkbox
                    checked={c.enabled}
                    onCheckedChange={() => handleToggle(c.key)}
                    className="mt-0.5"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{c.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {c.description}
                    </p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Auto-outreach toggle (Phase 2 — disabled for now) */}
          <div className="rounded-md border p-3 opacity-50">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">
                  Auto-contact landlord
                </p>
                <p className="text-xs text-muted-foreground">
                  Auto-send message when score reaches threshold
                </p>
              </div>
              <Badge variant="outline" className="text-[10px]">
                Coming soon
              </Badge>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-4 flex gap-2">
          <Button
            className="flex-1"
            onClick={handleStart}
            disabled={loading || enabledCount === 0}
          >
            {loading ? "Starting..." : "Start research"}
          </Button>
          <Button
            variant="outline"
            onClick={() => setConfigSheetOpen(false)}
          >
            Cancel
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
