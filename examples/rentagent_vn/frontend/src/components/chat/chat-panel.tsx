"use client";

import { useRef, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { ChatInput } from "./chat-input";
import { ChatMessage } from "./chat-message";
import { useChatStore } from "@/stores/chat-store";
import { useWebSocket } from "@/hooks/use-websocket";

interface ChatPanelProps {
  open: boolean;
  onClose: () => void;
  contextId: string;
}

export function ChatPanel({ open, onClose, contextId }: ChatPanelProps) {
  const { messages, isTyping, wsStatus } = useChatStore();
  const { sendMessage } = useWebSocket(contextId);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <Sheet open={open} onOpenChange={() => onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-md flex flex-col p-0">
        <SheetHeader className="px-4 py-3 border-b">
          <div className="flex items-center justify-between">
            <SheetTitle className="text-base">Chat with assistant</SheetTitle>
            <Badge
              variant={wsStatus === "connected" ? "default" : "secondary"}
              className="text-xs"
            >
              {wsStatus === "connected"
                ? "Connected"
                : wsStatus === "connecting"
                ? "Connecting..."
                : "Disconnected"}
            </Badge>
          </div>
        </SheetHeader>

        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          <div className="space-y-3">
            {messages.length === 0 && (
              <p className="text-sm text-muted-foreground text-center py-8">
                Ask the assistant anything about your rental search.
              </p>
            )}
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {isTyping && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-lg px-3 py-2 text-sm">
                  <span className="animate-pulse">Typing...</span>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="border-t p-3">
          <ChatInput
            onSend={sendMessage}
            disabled={wsStatus !== "connected"}
          />
        </div>
      </SheetContent>
    </Sheet>
  );
}
