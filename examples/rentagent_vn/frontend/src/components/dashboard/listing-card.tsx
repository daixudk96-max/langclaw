"use client";

import { MapPin, Bed, Maximize2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { useListingStore } from "@/stores/listing-store";
import { useResearchStore } from "@/stores/research-store";
import { ResearchProgress } from "./research-progress";
import { ResearchLivePreview } from "./research-live-preview";
import type { Listing } from "@/types";

interface ListingCardProps {
  listing: Listing;
  campaignId: string;
  selectable?: boolean;
}

const PLATFORM_LABELS: Record<string, string> = {
  facebook: "FB",
  "nhatot.com": "NT",
  "batdongsan.com.vn": "BDS",
};

const MAX_VISIBLE_BADGES = 3;

export function ListingCard({ listing, selectable }: ListingCardProps) {
  const { selectListing } = useListingStore();
  const {
    selectedIds,
    toggleSelection,
    researching,
    researchByListing,
    liveState,
  } = useResearchStore();

  const isSelected = selectedIds.has(listing.id);
  const researchId = listing.research_id || researchByListing[listing.id];
  const research = researchId ? researching[researchId] : undefined;
  const live = researchId ? liveState[researchId] : undefined;

  const isRunning = research?.status === "running";

  const platformLabel =
    PLATFORM_LABELS[listing.source_platform || ""] ||
    listing.source_platform?.slice(0, 3)?.toUpperCase() ||
    "";

  const badges: { label: string; className?: string }[] = [];
  if (platformLabel) {
    badges.push({ label: platformLabel });
  }
  if (listing.landlord_phone) {
    badges.push({ label: "Zalo", className: "text-green-600" });
  }

  const visibleBadges = badges.slice(0, MAX_VISIBLE_BADGES);
  const overflowCount = badges.length - MAX_VISIBLE_BADGES;

  const handleClick = () => {
    if (selectable && listing.stage === "new") {
      toggleSelection(listing.id);
    } else {
      selectListing(listing);
    }
  };

  const handleCheckboxClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    toggleSelection(listing.id);
  };

  return (
    <Card
      className={`relative p-3 cursor-pointer hover:shadow-md transition-shadow border-border/50 ${
        isSelected ? "ring-2 ring-teal-500 border-teal-300" : ""
      }`}
      onClick={handleClick}
    >
      {/* Invisible drag handle for future DnD */}
      <div className="absolute inset-x-0 top-0 h-2 cursor-grab opacity-0 hover:opacity-50 bg-muted rounded-t-lg" />

      <div className="flex gap-3">
        {/* Checkbox for selection mode */}
        {selectable && listing.stage === "new" && (
          <div
            className="flex items-start pt-1 shrink-0"
            onClick={handleCheckboxClick}
          >
            <Checkbox checked={isSelected} />
          </div>
        )}

        {/* Thumbnail with 4:3 aspect ratio */}
        {listing.thumbnail_url ? (
          <img
            src={listing.thumbnail_url}
            alt=""
            className="w-16 aspect-[4/3] rounded-md object-cover bg-muted shrink-0"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.style.display = "none";
              e.currentTarget.nextElementSibling?.classList.remove("hidden");
            }}
          />
        ) : null}
        <div
          className={`w-16 aspect-[4/3] rounded-md bg-muted flex items-center justify-center shrink-0 ${
            listing.thumbnail_url ? "hidden" : ""
          }`}
        >
          <Maximize2 className="h-4 w-4 text-muted-foreground" />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">
            {listing.title || "No title"}
          </p>

          {/* Price */}
          <p className="text-sm font-semibold text-primary mt-0.5 truncate">
            {listing.price_display || formatPrice(listing.price_vnd)}
          </p>

          {/* Meta */}
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            {listing.district && (
              <span className="flex items-center gap-0.5 truncate">
                <MapPin className="h-3 w-3 shrink-0" />
                <span className="truncate">{listing.district}</span>
              </span>
            )}
            {listing.bedrooms != null && (
              <span className="flex items-center gap-0.5 shrink-0">
                <Bed className="h-3 w-3" />
                {listing.bedrooms}BR
              </span>
            )}
            {listing.area_sqm != null && (
              <span className="shrink-0">{listing.area_sqm}m²</span>
            )}
          </div>
        </div>
      </div>

      {/* Research progress (for non-running states) */}
      {(listing.stage === "researching" || research) && !isRunning && (
        <div className="mt-2">
          <ResearchProgress research={research} compact />
        </div>
      )}

      {/* Live preview (for running state) */}
      {isRunning && (
        <ResearchLivePreview
          browserUrl={live?.browserUrl || null}
          currentDetail={live?.currentDetail || null}
          className="mt-3"
        />
      )}

      {/* Bottom badges with overflow */}
      <div className="flex items-center gap-1.5 mt-2 flex-nowrap overflow-hidden">
        {visibleBadges.map((badge, idx) => (
          <Badge
            key={idx}
            variant="outline"
            className={`text-[10px] h-4 px-1 shrink-0 ${badge.className || ""}`}
          >
            {badge.label}
          </Badge>
        ))}
        {overflowCount > 0 && (
          <Badge variant="secondary" className="text-[10px] h-4 px-1 shrink-0">
            +{overflowCount}
          </Badge>
        )}
      </div>
    </Card>
  );
}

function formatPrice(priceVnd: number | null): string {
  if (!priceVnd) return "Contact";
  if (priceVnd >= 1_000_000) {
    return `${(priceVnd / 1_000_000).toFixed(1).replace(".0", "")}M/mo`;
  }
  return `${priceVnd.toLocaleString("en-US")}d/mo`;
}
