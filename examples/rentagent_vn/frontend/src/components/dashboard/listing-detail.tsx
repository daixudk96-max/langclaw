"use client";

import { useState, useEffect, useRef } from "react";
import {
  MapPin,
  Phone,
  ExternalLink,
  Bed,
  Bath,
  Maximize2,
  X,
  MessageCircle,
  Send,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useListingStore } from "@/stores/listing-store";
import { useResearchStore } from "@/stores/research-store";
import { SkipDialog } from "./skip-dialog";
import { OutreachDialog } from "./outreach-dialog";
import { ResearchResults } from "./research-results";
import { ResearchProgress } from "./research-progress";
import { ZaloSettingsDialog } from "@/components/zalo/zalo-settings-dialog";
import { PIPELINE_STAGES, OUTREACH_STATUS_LABELS } from "@/types";
import type { Listing, PipelineStage, OutreachMessage } from "@/types";
import * as api from "@/lib/api";

interface ListingDetailProps {
  listing: Listing;
  campaignId: string;
  onClose: () => void;
}

export function ListingDetail({
  listing,
  campaignId,
  onClose,
}: ListingDetailProps) {
  const { updateStage, updateNotes, fetchListings } = useListingStore();
  const { researching, researchByListing } = useResearchStore();
  const [notes, setNotes] = useState(listing.user_notes || "");
  const [skipOpen, setSkipOpen] = useState(false);
  const [outreachOpen, setOutreachOpen] = useState(false);
  const [zaloSettingsOpen, setZaloSettingsOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [outreachHistory, setOutreachHistory] = useState<OutreachMessage[]>([]);

  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isInitialMount = useRef(true);

  useEffect(() => {
    api.getOutreachHistory(campaignId, listing.id).then(setOutreachHistory).catch(() => {});
  }, [campaignId, listing.id]);

  useEffect(() => {
    setNotes(listing.user_notes || "");
    isInitialMount.current = true;
  }, [listing.id]);

  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      if (notes !== (listing.user_notes || "")) {
        setSaving(true);
        await updateNotes(campaignId, listing.id, notes);
        setSaving(false);
      }
    }, 2000);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [notes, listing.user_notes, listing.id, campaignId, updateNotes]);

  const latestOutreach = outreachHistory[0];
  const outreachStatus = latestOutreach?.status;

  const handleStageChange = async (stage: PipelineStage) => {
    if (stage === "skipped") {
      setSkipOpen(true);
      return;
    }
    await updateStage(campaignId, listing.id, stage);
  };

  const handleNotesBlur = async () => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    if (notes !== (listing.user_notes || "")) {
      setSaving(true);
      await updateNotes(campaignId, listing.id, notes);
      setSaving(false);
    }
  };

  return (
    <>
      <Sheet open onOpenChange={() => onClose()}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-lg pr-6 leading-tight">
              {listing.title?.replace(/\s*·\s*null/gi, '').replace(/null\s*·\s*/gi, '').trim() || "Listing details"}
            </SheetTitle>
          </SheetHeader>

          <div className="mt-6 flex flex-col gap-6 px-1">
            {/* Thumbnail with aspect ratio and fallback */}
            {listing.thumbnail_url ? (
              <div className="w-full aspect-video rounded-xl overflow-hidden bg-muted border">
                <img
                  src={listing.thumbnail_url}
                  alt={listing.title || "Property image"}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                    const parent = (e.target as HTMLImageElement).parentElement;
                    if (parent) {
                      parent.classList.add('flex', 'items-center', 'justify-center');
                      parent.innerHTML = '<span class="text-muted-foreground text-sm">Failed to load image</span>';
                    }
                  }}
                />
              </div>
            ) : (
              <div className="w-full aspect-video rounded-xl bg-muted border flex items-center justify-center text-muted-foreground text-sm">
                No image available
              </div>
            )}

            {/* Price */}
            <div>
              <p className="text-2xl font-bold">
                {listing.price_display || formatPrice(listing.price_vnd)}
              </p>
              {listing.deposit_vnd && (
                <p className="text-sm text-muted-foreground">
                  Deposit: {formatPrice(listing.deposit_vnd)}
                </p>
              )}
            </div>

            {/* Key info grid */}
            <div className="grid grid-cols-2 gap-3">
              {listing.area_sqm != null && (
                <InfoItem
                  icon={<Maximize2 className="h-4 w-4" />}
                  label="Area"
                  value={`${listing.area_sqm} m²`}
                />
              )}
              {listing.bedrooms != null && (
                <InfoItem
                  icon={<Bed className="h-4 w-4" />}
                  label="Bedrooms"
                  value={`${listing.bedrooms} BR`}
                />
              )}
              {listing.bathrooms != null && (
                <InfoItem
                  icon={<Bath className="h-4 w-4" />}
                  label="Bathrooms"
                  value={`${listing.bathrooms} BA`}
                />
              )}
              {listing.district && (
                <InfoItem
                  icon={<MapPin className="h-4 w-4" />}
                  label="District"
                  value={listing.district}
                />
              )}
            </div>

            {/* Address */}
            {listing.address && (
              <div>
                <p className="text-sm font-medium mb-1">Address</p>
                <p className="text-sm text-muted-foreground">
                  {listing.address}
                </p>
              </div>
            )}

            <Separator />

            {/* Research results (if available) */}
            {(() => {
              const rid = listing.research_id || researchByListing[listing.id];
              const research = rid ? researching[rid] : undefined;
              if (research && research.status === "done" && research.scores) {
                return (
                  <div className="rounded-lg border border-teal-200 bg-teal-50/30 dark:bg-teal-950/20 p-4">
                    <ResearchResults
                      research={research}
                      campaignId={campaignId}
                      listingId={listing.id}
                    />
                  </div>
                );
              }
              if (research && (research.status === "running" || research.status === "queued")) {
                return (
                  <div className="rounded-lg border p-3">
                    <ResearchProgress research={research} />
                  </div>
                );
              }
              return null;
            })()}

            {/* Description */}
            {listing.description && (
              <>
                <Separator />
                <div>
                  <p className="text-sm font-medium mb-1">Description</p>
                  <p className="text-sm text-muted-foreground whitespace-pre-line line-clamp-6">
                    {listing.description}
                  </p>
                </div>
              </>
            )}

            <Separator />

            {/* Status */}
            <div>
              <p className="text-sm font-medium mb-2">Status</p>
              <div className="flex gap-2">
                <Select
                  value={listing.stage}
                  onValueChange={(v) =>
                    handleStageChange(v as PipelineStage)
                  }
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PIPELINE_STAGES.map((s) => (
                      <SelectItem key={s.key} value={s.key}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {listing.skip_reason && (
                <p className="text-xs text-muted-foreground mt-1">
                  Skip reason: {listing.skip_reason}
                </p>
              )}
            </div>

            {/* Notes */}
            <div>
              <p className="text-sm font-medium mb-1.5">Notes</p>
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                onBlur={handleNotesBlur}
                placeholder="Add your notes for this listing..."
                rows={3}
                className="text-sm"
              />
              {saving && (
                <p className="text-xs text-muted-foreground mt-1">
                  Saving...
                </p>
              )}
            </div>

            <Separator />

            {/* Contact Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold">Contact</p>
                {outreachStatus && (
                  <Badge
                    variant={outreachStatus === "sent" || outreachStatus === "replied" ? "default" : "secondary"}
                    className="text-xs"
                  >
                    {OUTREACH_STATUS_LABELS[outreachStatus]}
                  </Badge>
                )}
              </div>

              {listing.landlord_name && (
                <p className="text-sm text-muted-foreground">{listing.landlord_name}</p>
              )}

              {/* Primary CTA */}
              {listing.landlord_phone && (
                <Button onClick={() => setOutreachOpen(true)} className="w-full" size="lg">
                  <Send className="h-4 w-4 mr-2" />
                  Contact landlord
                </Button>
              )}

              {/* Secondary actions */}
              <div className="flex flex-wrap gap-2">
                {listing.landlord_phone && (
                  <>
                    <Button variant="outline" size="sm" asChild>
                      <a href={`tel:${listing.landlord_phone}`}>
                        <Phone className="h-3.5 w-3.5 mr-1.5" />
                        Call
                      </a>
                    </Button>
                    <Button variant="outline" size="sm" asChild>
                      <a
                        href={`https://zalo.me/${listing.landlord_phone}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <MessageCircle className="h-3.5 w-3.5 mr-1.5" />
                        Zalo
                      </a>
                    </Button>
                  </>
                )}
                {listing.landlord_facebook_url && (
                  <Button variant="outline" size="sm" asChild>
                    <a
                      href={listing.landlord_facebook_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                      Facebook
                    </a>
                  </Button>
                )}
              </div>
            </div>

            {/* Source link + Platform metadata */}
            <div className="flex items-center justify-between text-xs text-muted-foreground pt-2">
              <div className="flex items-center gap-2">
                {listing.source_platform && (
                  <Badge variant="outline" className="text-xs">
                    {listing.source_platform}
                  </Badge>
                )}
                {listing.posted_date && (
                  <span>Posted: {listing.posted_date}</span>
                )}
              </div>
              {listing.listing_url && (
                <Button variant="link" size="sm" className="px-0 h-auto" asChild>
                  <a
                    href={listing.listing_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink className="h-3.5 w-3.5 mr-1" />
                    View original
                  </a>
                </Button>
              )}
            </div>
          </div>
        </SheetContent>
      </Sheet>

      <SkipDialog
        open={skipOpen}
        onClose={() => setSkipOpen(false)}
        onSkip={async (reason) => {
          await updateStage(campaignId, listing.id, "skipped", reason);
          setSkipOpen(false);
        }}
      />

      <OutreachDialog
        open={outreachOpen}
        onClose={() => setOutreachOpen(false)}
        listing={listing}
        campaignId={campaignId}
        onZaloSettingsOpen={() => setZaloSettingsOpen(true)}
        onSuccess={() => {
          api.getOutreachHistory(campaignId, listing.id).then(setOutreachHistory).catch(() => {});
          fetchListings(campaignId);
        }}
      />

      <ZaloSettingsDialog
        open={zaloSettingsOpen}
        onClose={() => setZaloSettingsOpen(false)}
      />
    </>
  );
}

function InfoItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2 p-2 rounded-md bg-muted/50">
      <div className="text-muted-foreground">{icon}</div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-medium">{value}</p>
      </div>
    </div>
  );
}

function formatPrice(priceVnd: number | null): string {
  if (!priceVnd) return "Contact";
  if (priceVnd >= 1_000_000) {
    return `${(priceVnd / 1_000_000).toFixed(1).replace(".0", "")}M/month`;
  }
  return `${priceVnd.toLocaleString("en-US")}d/month`;
}
