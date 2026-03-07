"use client";

import { useState, useEffect } from "react";
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

  useEffect(() => {
    api.getOutreachHistory(campaignId, listing.id).then(setOutreachHistory).catch(() => {});
  }, [campaignId, listing.id]);

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
            <SheetTitle className="text-base pr-6">
              {listing.title || "Chi tiết tin đăng"}
            </SheetTitle>
          </SheetHeader>

          <div className="mt-4 space-y-5">
            {/* Thumbnail */}
            {listing.thumbnail_url && (
              <img
                src={listing.thumbnail_url}
                alt=""
                className="w-full h-48 object-cover rounded-lg bg-muted"
              />
            )}

            {/* Research results (if available) */}
            {(() => {
              const rid = listing.research_id || researchByListing[listing.id];
              const research = rid ? researching[rid] : undefined;
              if (research && research.status === "done" && research.scores) {
                return (
                  <>
                    <div className="rounded-lg border border-teal-200 bg-teal-50/30 p-4">
                      <ResearchResults
                        research={research}
                        campaignId={campaignId}
                        listingId={listing.id}
                      />
                    </div>
                    <Separator />
                  </>
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

            {/* Price */}
            <div>
              <p className="text-2xl font-bold">
                {listing.price_display || formatPrice(listing.price_vnd)}
              </p>
              {listing.deposit_vnd && (
                <p className="text-sm text-muted-foreground">
                  Cọc: {formatPrice(listing.deposit_vnd)}
                </p>
              )}
            </div>

            {/* Key info grid */}
            <div className="grid grid-cols-2 gap-3">
              {listing.area_sqm != null && (
                <InfoItem
                  icon={<Maximize2 className="h-4 w-4" />}
                  label="Diện tích"
                  value={`${listing.area_sqm} m²`}
                />
              )}
              {listing.bedrooms != null && (
                <InfoItem
                  icon={<Bed className="h-4 w-4" />}
                  label="Phòng ngủ"
                  value={`${listing.bedrooms} PN`}
                />
              )}
              {listing.bathrooms != null && (
                <InfoItem
                  icon={<Bath className="h-4 w-4" />}
                  label="Phòng tắm"
                  value={`${listing.bathrooms} PT`}
                />
              )}
              {listing.district && (
                <InfoItem
                  icon={<MapPin className="h-4 w-4" />}
                  label="Khu vực"
                  value={listing.district}
                />
              )}
            </div>

            {/* Address */}
            {listing.address && (
              <div>
                <p className="text-sm font-medium mb-1">Địa chỉ</p>
                <p className="text-sm text-muted-foreground">
                  {listing.address}
                </p>
              </div>
            )}

            {/* Description */}
            {listing.description && (
              <div>
                <p className="text-sm font-medium mb-1">Mô tả</p>
                <p className="text-sm text-muted-foreground whitespace-pre-line">
                  {listing.description}
                </p>
              </div>
            )}

            <Separator />

            {/* Landlord contact */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium">Liên hệ</p>
                {outreachStatus && (
                  <Badge
                    variant={outreachStatus === "sent" || outreachStatus === "replied" ? "default" : "secondary"}
                    className="text-xs"
                  >
                    {OUTREACH_STATUS_LABELS[outreachStatus]}
                  </Badge>
                )}
              </div>
              <div className="space-y-3">
                {listing.landlord_name && (
                  <p className="text-sm">{listing.landlord_name}</p>
                )}

                {listing.landlord_phone && (
                  <Button
                    onClick={() => setOutreachOpen(true)}
                    className="w-full"
                  >
                    <Send className="h-4 w-4 mr-2" />
                    Liên hệ chủ nhà
                  </Button>
                )}

                <div className="flex gap-2">
                  {listing.landlord_phone && (
                    <>
                      <Button variant="outline" size="sm" asChild>
                        <a href={`tel:${listing.landlord_phone}`}>
                          <Phone className="h-3.5 w-3.5 mr-1" />
                          {listing.landlord_phone}
                        </a>
                      </Button>
                      <Button variant="outline" size="sm" asChild>
                        <a
                          href={`https://zalo.me/${listing.landlord_phone}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <MessageCircle className="h-3.5 w-3.5 mr-1" />
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
                        <ExternalLink className="h-3.5 w-3.5 mr-1" />
                        Facebook
                      </a>
                    </Button>
                  )}
                </div>
              </div>
            </div>

            {/* Source link */}
            {listing.listing_url && (
              <Button variant="link" size="sm" className="px-0" asChild>
                <a
                  href={listing.listing_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ExternalLink className="h-3.5 w-3.5 mr-1" />
                  Xem bài gốc
                </a>
              </Button>
            )}

            <Separator />

            {/* Actions */}
            <div>
              <p className="text-sm font-medium mb-2">Trạng thái</p>
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
                  Lý do bỏ qua: {listing.skip_reason}
                </p>
              )}
            </div>

            {/* Notes */}
            <div>
              <p className="text-sm font-medium mb-1.5">Ghi chú</p>
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                onBlur={handleNotesBlur}
                placeholder="Thêm ghi chú riêng cho tin này..."
                rows={3}
                className="text-sm"
              />
              {saving && (
                <p className="text-xs text-muted-foreground mt-1">
                  Đang lưu...
                </p>
              )}
            </div>

            {/* Platform + date metadata */}
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {listing.source_platform && (
                <Badge variant="outline" className="text-xs">
                  {listing.source_platform}
                </Badge>
              )}
              {listing.posted_date && (
                <span>Đăng: {listing.posted_date}</span>
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
  if (!priceVnd) return "Liên hệ";
  if (priceVnd >= 1_000_000) {
    return `${(priceVnd / 1_000_000).toFixed(1).replace(".0", "")} triệu/tháng`;
  }
  return `${priceVnd.toLocaleString("vi-VN")} đ/tháng`;
}
