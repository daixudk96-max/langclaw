"use client";

import { useState } from "react";
import { Zap } from "lucide-react";
import { BottomSheet } from "@/components/ui/bottom-sheet";

interface OutreachConsentSheetProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (autoSend: boolean) => void;
}

export function OutreachConsentSheet({
  open,
  onClose,
  onConfirm,
}: OutreachConsentSheetProps) {
  const [selected, setSelected] = useState<"auto" | "review">("review");

  const handleContinue = () => {
    onConfirm(selected === "auto");
    onClose();
  };

  return (
    <BottomSheet open={open} onClose={onClose} title="" maxHeight="auto">
      <div className="px-5 pb-6">
        {/* Icon + Title */}
        <div className="flex items-center gap-2 mb-2">
          <div
            className="flex items-center justify-center rounded-full"
            style={{
              width: 32,
              height: 32,
              background: "var(--amber-15)",
            }}
          >
            <Zap size={16} style={{ color: "var(--amber)" }} />
          </div>
          <h2
            className="text-[22px] font-extrabold"
            style={{ color: "var(--ink)", letterSpacing: "-0.8px" }}
          >
            Quick Contact
          </h2>
        </div>

        {/* Description */}
        <p
          className="text-[14px] mb-4"
          style={{ color: "var(--ink-50)" }}
        >
          When you tap Contact now, I'll draft a message to the landlord.
        </p>

        {/* Radio options */}
        <div
          className="rounded-xl overflow-hidden"
          style={{ border: "1px solid var(--ink-08)" }}
        >
          {/* Auto-send option */}
          <button
            onClick={() => setSelected("auto")}
            className="w-full flex items-start gap-3 p-4 text-left transition-colors"
            style={{
              background: selected === "auto" ? "var(--terra-08)" : "var(--white)",
              borderBottom: "1px solid var(--ink-04)",
            }}
          >
            <div
              className="flex-shrink-0 mt-0.5 flex items-center justify-center rounded-full"
              style={{
                width: 20,
                height: 20,
                border: `2px solid ${selected === "auto" ? "var(--terra)" : "var(--ink-15)"}`,
                background: selected === "auto" ? "var(--terra)" : "transparent",
              }}
            >
              {selected === "auto" && (
                <div
                  className="rounded-full"
                  style={{ width: 8, height: 8, background: "white" }}
                />
              )}
            </div>
            <div>
              <p
                className="text-[14px] font-semibold"
                style={{ color: "var(--ink)" }}
              >
                Auto-send
              </p>
              <p
                className="text-[12px]"
                style={{ color: "var(--ink-30)" }}
              >
                Send immediately after drafting
              </p>
            </div>
          </button>

          {/* Review first option */}
          <button
            onClick={() => setSelected("review")}
            className="w-full flex items-start gap-3 p-4 text-left transition-colors"
            style={{
              background: selected === "review" ? "var(--terra-08)" : "var(--white)",
            }}
          >
            <div
              className="flex-shrink-0 mt-0.5 flex items-center justify-center rounded-full"
              style={{
                width: 20,
                height: 20,
                border: `2px solid ${selected === "review" ? "var(--terra)" : "var(--ink-15)"}`,
                background: selected === "review" ? "var(--terra)" : "transparent",
              }}
            >
              {selected === "review" && (
                <div
                  className="rounded-full"
                  style={{ width: 8, height: 8, background: "white" }}
                />
              )}
            </div>
            <div>
              <p
                className="text-[14px] font-semibold"
                style={{ color: "var(--ink)" }}
              >
                Review first
              </p>
              <p
                className="text-[12px]"
                style={{ color: "var(--ink-30)" }}
              >
                I'll notify you to review before sending
              </p>
            </div>
          </button>
        </div>

        {/* Continue button */}
        <button
          onClick={handleContinue}
          className="w-full mt-4 py-3 rounded-xl text-[14px] font-semibold text-white transition-transform active:scale-[0.98]"
          style={{ background: "var(--terra)" }}
        >
          Continue
        </button>

        {/* Footer hint */}
        <p
          className="text-[12px] text-center mt-3"
          style={{ color: "var(--ink-30)" }}
        >
          You can change this in Settings
        </p>
      </div>
    </BottomSheet>
  );
}
