"use client";

import { MapPin, Bed, Maximize2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { useListingStore } from "@/stores/listing-store";
import { useResearchStore } from "@/stores/research-store";
import { ResearchProgress } from "./research-progress";
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

export function ListingCard({ listing, selectable }: ListingCardProps) {
  const { selectListing } = useListingStore();
  const { selectedIds, toggleSelection, researching, researchByListing } =
    useResearchStore();

  const isSelected = selectedIds.has(listing.id);
  const researchId = listing.research_id || researchByListing[listing.id];
  const research = researchId ? researching[researchId] : undefined;

  const platformLabel =
    PLATFORM_LABELS[listing.source_platform || ""] ||
    listing.source_platform?.slice(0, 3)?.toUpperCase() ||
    "";

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
      className={`p-3 cursor-pointer hover:shadow-md transition-shadow border-border/50 ${
        isSelected ? "ring-2 ring-teal-500 border-teal-300" : ""
      }`}
      onClick={handleClick}
    >
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

        {/* Thumbnail */}
        {listing.thumbnail_url ? (
          <img
            src={listing.thumbnail_url}
            alt=""
            className="w-16 h-16 rounded-md object-cover bg-muted shrink-0"
            loading="lazy"
          />
        ) : (
          <div className="w-16 h-16 rounded-md bg-muted flex items-center justify-center shrink-0">
            <Maximize2 className="h-4 w-4 text-muted-foreground" />
          </div>
        )}

        {/* Info */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">
            {listing.title || "Không có tiêu đề"}
          </p>

          {/* Price */}
          <p className="text-sm font-semibold text-primary mt-0.5">
            {listing.price_display || formatPrice(listing.price_vnd)}
          </p>

          {/* Meta */}
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            {listing.district && (
              <span className="flex items-center gap-0.5">
                <MapPin className="h-3 w-3" />
                {listing.district}
              </span>
            )}
            {listing.bedrooms != null && (
              <span className="flex items-center gap-0.5">
                <Bed className="h-3 w-3" />
                {listing.bedrooms}PN
              </span>
            )}
            {listing.area_sqm != null && (
              <span>{listing.area_sqm}m²</span>
            )}
          </div>
        </div>
      </div>

      {/* Research progress (for researching stage) */}
      {(listing.stage === "researching" || research) && (
        <div className="mt-2">
          <ResearchProgress research={research} compact />
        </div>
      )}

      {/* Bottom badges */}
      <div className="flex items-center gap-1.5 mt-2">
        {platformLabel && (
          <Badge variant="outline" className="text-[10px] h-4 px-1">
            {platformLabel}
          </Badge>
        )}
        {listing.landlord_phone && (
          <Badge variant="outline" className="text-[10px] h-4 px-1 text-green-600">
            Zalo
          </Badge>
        )}
      </div>
    </Card>
  );
}

function formatPrice(priceVnd: number | null): string {
  if (!priceVnd) return "Liên hệ";
  if (priceVnd >= 1_000_000) {
    return `${(priceVnd / 1_000_000).toFixed(1).replace(".0", "")} triệu/th`;
  }
  return `${priceVnd.toLocaleString("vi-VN")} đ/th`;
}
