"use client";

import { useListingStore } from "@/stores/listing-store";
import { TrackSection } from "./track-section";

interface TrackScreenProps {
  campaignId: string;
  campaignPill?: React.ReactNode;
}

export function TrackScreen({ campaignId, campaignPill }: TrackScreenProps) {
  // Use selector to avoid subscribing to entire store
  const listings = useListingStore((s) => s.listings);

  // Filter by sections per PRD stage mapping
  const pendingReview = listings.filter((l) => l.stage === "pending_review");
  const researching = listings.filter((l) => l.stage === "researching");
  const contacted = listings.filter(
    (l) => l.stage === "contacted" || l.stage === "viewing"
  );
  const done = listings.filter(
    (l) => l.stage === "viewed" || l.stage === "shortlisted"
  );

  const total = pendingReview.length + researching.length + contacted.length + done.length;

  return (
    <div
      className="flex flex-col h-full overflow-hidden"
      style={{ background: "var(--cream)" }}
    >
      {/* Sticky header */}
      <div
        className="flex-shrink-0 px-5 pt-4 pb-3"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 20,
          background: "var(--cream)",
          borderBottom: "1px solid var(--ink-04)",
        }}
      >
        {/* Campaign pill */}
        <div className="mb-2">{campaignPill}</div>
        <h1
          className="text-[22px] font-extrabold"
          style={{ color: "var(--ink)", letterSpacing: "-0.8px" }}
        >
          Tracking
        </h1>
        <p className="text-[13px] mt-0.5" style={{ color: "var(--ink-50)" }}>
          {total} listings in progress
        </p>
      </div>

      {/* Scrollable content */}
      <div
        className="flex-1 overflow-y-auto px-5 py-4 space-y-6"
        style={{ paddingBottom: 32 }}
      >
        {total === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-[15px] font-medium" style={{ color: "var(--ink-30)" }}>
              No listings being tracked
            </p>
            <p className="text-[13px] mt-1" style={{ color: "var(--ink-30)" }}>
              Swipe right to add listings to your list
            </p>
          </div>
        ) : (
          <>
            <TrackSection
              title="Pending Review"
              dotColor="var(--amber)"
              listings={pendingReview}
              campaignId={campaignId}
              pulseDot
            />
            <TrackSection
              title="Researching"
              dotColor="var(--amber)"
              listings={researching}
              campaignId={campaignId}
            />
            <TrackSection
              title="Contacted"
              dotColor="var(--terra)"
              listings={contacted}
              campaignId={campaignId}
            />
            <TrackSection
              title="Done"
              dotColor="var(--ink-30)"
              listings={done}
              collapsedByDefault={done.length > 0}
              campaignId={campaignId}
            />
          </>
        )}
      </div>
    </div>
  );
}
