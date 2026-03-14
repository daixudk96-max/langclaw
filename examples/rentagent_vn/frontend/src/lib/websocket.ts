/**
 * WebSocket connection manager for real-time chat with the Langclaw agent.
 *
 * Connects to the Langclaw WebSocket gateway and provides:
 * - Auto-reconnect with exponential backoff
 * - Event-based message handling
 * - Typed message protocol
 */

import type { WSOutbound } from "@/types";

type MessageHandler = (msg: WSOutbound) => void;
type StatusHandler = (status: "connecting" | "connected" | "disconnected") => void;

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:18789";

const MAX_RECONNECT_DELAY = 30_000;
const INITIAL_RECONNECT_DELAY = 1_000;
const PING_INTERVAL = 30_000;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private messageHandlers = new Set<MessageHandler>();
  private statusHandlers = new Set<StatusHandler>();
  private reconnectDelay = INITIAL_RECONNECT_DELAY;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private userId: string;
  private contextId: string;
  private shouldReconnect = true;

  constructor(userId: string, contextId: string) {
    this.userId = userId;
    this.contextId = contextId;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.notifyStatus("connecting");

    try {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => {
        this.reconnectDelay = INITIAL_RECONNECT_DELAY;
        this.notifyStatus("connected");
        this.startPing();
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WSOutbound;
          this.messageHandlers.forEach((h) => h(msg));
        } catch {
          console.error("Failed to parse WS message:", event.data);
        }
      };

      this.ws.onclose = () => {
        this.stopPing();
        this.notifyStatus("disconnected");
        if (this.shouldReconnect) this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        // onclose will fire after this
      };
    } catch {
      this.notifyStatus("disconnected");
      if (this.shouldReconnect) this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.stopPing();
    this.ws?.close();
    this.ws = null;
  }

  send(content: string, metadata?: Record<string, unknown>): void {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn("WebSocket not connected, cannot send");
      return;
    }
    this.ws.send(
      JSON.stringify({
        type: "message",
        content,
        user_id: this.userId,
        context_id: this.contextId,
        metadata,
      })
    );
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  updateContext(contextId: string): void {
    this.contextId = contextId;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private notifyStatus(status: "connecting" | "connected" | "disconnected"): void {
    this.statusHandlers.forEach((h) => h(status));
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_DELAY);
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
      }
    }, PING_INTERVAL);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }
}
