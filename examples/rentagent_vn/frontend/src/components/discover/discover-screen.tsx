"use client";

import { useCallback, useEffect, useState, useRef } from "react";
import { toast } from "sonner";
import { useListingStore } from "@/stores/listing-store";
import { useResearchStore } from "@/stores/research-store";
import { useCampaignStore } from "@/stores/campaign-store";
import { useScanStreamStore } from "@/stores/scan-stream-store";
import { useActivityStore } from "@/stores/activity-store";
import { useZaloStore } from "@/stores/zalo-store";
import * as api from "@/lib/api";
import type { Listing } from "@/types";
import { CardStack } from "./card-stack";
import { ActionBar } from "./action-bar";
import { EmptyDiscover } from "./empty-discover";
import { ScanLiveSheet } from "./scan-live-sheet";
import { OutreachConsentSheet } from "./outreach-consent-sheet";
import { ListingDetailSheet } from "@/components/listing";

interface DiscoverScreenProps {
  campaignId: string;
  campaignPill?: React.ReactNode;
}

export function DiscoverScreen({ campaignId, campaignPill }: DiscoverScreenProps) {
  // Use selectors to avoid subscribing to entire stores
  const listings = useListingStore((s) => s.listings);
  const fetchListings = useListingStore((s) => s.fetchListings);
  const researching = useResearchStore((s) => s.researching);
  const researchByListing = useResearchStore((s) => s.researchByListing);
  const campaign = useCampaignStore((s) => s.campaign);
  const setOutreachAutoSend = useCampaignStore((s) => s.setOutreachAutoSend);
  const scanStatus = useScanStreamStore((s) => s.status);
  const isScanning = useActivityStore((s) => s.isScanning);
  const triggerScan = useActivityStore((s) => s.triggerScan);
  const zaloStatus = useZaloStore((s) => s.status);
  const fetchZaloStatus = useZaloStore((s) => s.fetchStatus);
  const [scanSheetOpen, setScanSheetOpen] = useState(false);
  const [removing, setRemoving] = useState<Set<string>>(new Set());
  const [detailListing, setDetailListing] = useState<Listing | null>(null);
  const [consentSheetOpen, setConsentSheetOpen] = useState(false);
  const pendingContactRef = useRef<Listing | null>(null);

  // Only new listings
  const newListings = listings.filter(
    (l) => l.stage === "new" && !removing.has(l.id)
  );

  // Show scan indicator if scanning or recent stream
  const showScanIndicator = isScanning || scanStatus === "streaming" || scanStatus === "connecting";

  // Auto-open scan sheet when scanning starts
  useEffect(() => {
    if (showScanIndicator) {
      // Don't auto-open; let user tap the indicator
    }
  }, [showScanIndicator]);

  // Auto-dismiss sheet and show toast when scan completes
  useEffect(() => {
    if (scanStatus === "complete") {
      setScanSheetOpen(false);
      const count = useScanStreamStore.getState().listingsFound;
      toast.success(`Scan complete · ${count} new listings`, { icon: "✓" });
      fetchListings(campaignId);
    }
  }, [scanStatus, campaignId, fetchListings]);

  // Fetch Zalo status on mount
  useEffect(() => {
    fetchZaloStatus();
  }, [fetchZaloStatus]);

  const getResearch = useCallback(
    (listing: Listing) => {
      const researchId = listing.research_id ?? researchByListing[listing.id];
      if (!researchId) return null;
      return researching[researchId] ?? null;
    },
    [researching, researchByListing]
  );

  const executeContact = useCallback(
    async (listing: Listing, autoSend: boolean) => {
      // Optimistic: remove card immediately
      setRemoving((prev) => new Set([...prev, listing.id]));

      try {
        // Check if listing has landlord phone
        if (!listing.landlord_phone) {
          toast.error("No contact info available for this listing");
          setRemoving((prev) => {
            const next = new Set(prev);
            next.delete(listing.id);
            return next;
          });
          return;
        }

        // Create AI draft
        const draft = await api.draftOutreach(campaignId, listing.id);

        if (autoSend) {
          // Auto-send the message
          try {
            await api.sendOutreach(campaignId, listing.id, draft.id);
            await api.updateListing(campaignId, listing.id, { stage: "contacted" });
            useListingStore.setState((s) => ({
              listings: s.listings.map((l) =>
                l.id === listing.id ? { ...l, stage: "contacted" } : l
              ),
            }));
            toast.success("Message sent to landlord");
          } catch {
            // Send failed, fall back to pending_review
            await api.updateListing(campaignId, listing.id, { stage: "pending_review" });
            useListingStore.setState((s) => ({
              listings: s.listings.map((l) =>
                l.id === listing.id ? { ...l, stage: "pending_review" } : l
              ),
            }));
            toast.error("Failed to send — review draft in Track tab");
          }
        } else {
          // Manual review: move to pending_review
          await api.updateListing(campaignId, listing.id, { stage: "pending_review" });
          useListingStore.setState((s) => ({
            listings: s.listings.map((l) =>
              l.id === listing.id ? { ...l, stage: "pending_review" } : l
            ),
          }));
          toast.info("Draft ready — review in Track tab");
        }
      } catch {
        // Revert: put card back
        setRemoving((prev) => {
          const next = new Set(prev);
          next.delete(listing.id);
          return next;
        });
        toast.error("Something went wrong, please try again");
      }
    },
    [campaignId]
  );

  const handleSwipe = useCallback(
    async (listing: Listing, direction: "like" | "skip" | "contact") => {
      if (direction === "contact") {
        // Check Zalo connection first
        const isConnected = zaloStatus?.connected ?? false;
        if (!isConnected) {
          toast.error("Connect Zalo in Settings to contact landlords");
          return;
        }

        // Check if preference is set
        const autoSendPref = campaign?.preferences?.outreach_auto_send;
        if (autoSendPref === undefined) {
          // Show consent modal, store pending listing
          pendingContactRef.current = listing;
          setConsentSheetOpen(true);
          return;
        }

        // Execute contact with the preference
        await executeContact(listing, autoSendPref);
        return;
      }

      // Optimistic: remove card immediately
      setRemoving((prev) => new Set([...prev, listing.id]));

      try {
        if (direction === "like") {
          // Trigger research — moves listing to "researching"
          const result = await api.triggerResearch(campaignId, {
            listing_ids: [listing.id],
            criteria: [], // use backend defaults
          });
          // Optimistically wire research_id
          if (result.research_ids[0]) {
            useListingStore.setState((s) => ({
              listings: s.listings.map((l) =>
                l.id === listing.id
                  ? { ...l, stage: "researching", research_id: result.research_ids[0] }
                  : l
              ),
            }));
          }
          // Refetch research data
          await useResearchStore.getState().fetchAllResearch(campaignId);
        } else if (direction === "skip") {
          await api.updateListing(campaignId, listing.id, {
            stage: "skipped",
            skip_reason: "other",
          });
          useListingStore.setState((s) => ({
            listings: s.listings.map((l) =>
              l.id === listing.id ? { ...l, stage: "skipped" } : l
            ),
          }));
        }
      } catch {
        // Revert: put card back
        setRemoving((prev) => {
          const next = new Set(prev);
          next.delete(listing.id);
          return next;
        });
        toast.error("Something went wrong, please try again");
      }
    },
    [campaignId, campaign?.preferences?.outreach_auto_send, zaloStatus?.connected, executeContact]
  );

  const handleConsentConfirm = useCallback(
    async (autoSend: boolean) => {
      // Save preference
      await setOutreachAutoSend(campaignId, autoSend);

      // Execute pending contact if any
      const listing = pendingContactRef.current;
      if (listing) {
        pendingContactRef.current = null;
        await executeContact(listing, autoSend);
      }
    },
    [campaignId, setOutreachAutoSend, executeContact]
  );

  const handleTriggerScan = async () => {
    try {
      await triggerScan(campaignId);
      setScanSheetOpen(true);
    } catch {
      toast.error("Failed to start scan");
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: "var(--cream)" }}>
      {/* Header */}
      <div
        className="flex-shrink-0 flex items-center justify-between"
        style={{ padding: "12px 20px" }}
      >
        {/* Campaign pill */}
        {campaignPill}

        {/* Right side: scan indicator or count badge */}
        <div className="flex items-center gap-2">
          {showScanIndicator ? (
            <button
              onClick={() => setScanSheetOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold"
              style={{
                background: "var(--amber-15)",
                color: "var(--amber)",
                borderRadius: "var(--r-full)",
              }}
            >
              <span className="pulse-dot">●</span> Scanning...
            </button>
          ) : (
            <>
              <div
                className="px-2.5 py-1 text-[12px] font-semibold text-white"
                style={{ background: "var(--terra)", borderRadius: "var(--r-full)" }}
              >
                {newListings.length} new
              </div>
              {/* "Quét ngay" replaces filter icon — filter icon is Phase 2 */}
              <button
                onClick={handleTriggerScan}
                className="px-3 py-1.5 text-[12px] font-semibold"
                style={{
                  background: "var(--ink-08)",
                  color: "var(--ink-50)",
                  borderRadius: "var(--r-full)",
                }}
              >
                Scan now
              </button>
            </>
          )}
        </div>
      </div>

      {/* Card stack or empty state */}
      {newListings.length === 0 ? (
        <EmptyDiscover />
      ) : (
        <>
          <div className="flex-1 relative overflow-hidden" style={{ padding: "0 16px" }}>
            <CardStack
              listings={newListings}
              getResearch={getResearch}
              onSwipe={handleSwipe}
              onTap={(listing) => setDetailListing(listing)}
            />
          </div>

          <ActionBar
            onSkip={() => newListings[0] && handleSwipe(newListings[0], "skip")}
            onLike={() => newListings[0] && handleSwipe(newListings[0], "like")}
            onContact={() => newListings[0] && handleSwipe(newListings[0], "contact")}
          />
        </>
      )}

      {/* Scan live sheet */}
      <ScanLiveSheet open={scanSheetOpen} onClose={() => setScanSheetOpen(false)} />

      {/* Listing detail sheet */}
      {detailListing && (
        <ListingDetailSheet
          open={!!detailListing}
          onClose={() => setDetailListing(null)}
          listing={detailListing}
          campaignId={campaignId}
          mode="discover"
          onLike={() => handleSwipe(detailListing, "like")}
          onSkip={() => handleSwipe(detailListing, "skip")}
          onContact={() => handleSwipe(detailListing, "contact")}
        />
      )}

      {/* Outreach consent sheet */}
      <OutreachConsentSheet
        open={consentSheetOpen}
        onClose={() => {
          setConsentSheetOpen(false);
          pendingContactRef.current = null;
        }}
        onConfirm={handleConsentConfirm}
      />
    </div>
  );
}
