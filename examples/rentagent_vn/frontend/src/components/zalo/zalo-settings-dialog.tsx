"use client";

import { useState, useEffect } from "react";
import { MessageCircle, Wifi, WifiOff, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useZaloStore } from "@/stores/zalo-store";

interface ZaloSettingsDialogProps {
  open: boolean;
  onClose: () => void;
}

export function ZaloSettingsDialog({ open, onClose }: ZaloSettingsDialogProps) {
  const { status, connecting, error, fetchStatus, connectCookie, disconnect, clearError } =
    useZaloStore();

  const [cookie, setCookie] = useState("");
  const [imei, setImei] = useState("");
  const [userAgent, setUserAgent] = useState("");

  useEffect(() => {
    if (open) {
      fetchStatus();
      if (typeof navigator !== "undefined") {
        setUserAgent(navigator.userAgent);
      }
    }
  }, [open, fetchStatus]);

  const handleConnect = async () => {
    if (!cookie.trim() || !imei.trim() || !userAgent.trim()) return;
    try {
      await connectCookie(cookie, imei, userAgent);
      setCookie("");
      setImei("");
    } catch {
      // Error handled in store
    }
  };

  const handleDisconnect = async () => {
    await disconnect();
  };

  const isConnected = status?.connected ?? false;

  return (
    <Dialog open={open} onOpenChange={() => onClose()}>
      <DialogContent className="sm:max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5" />
            Zalo Settings
          </DialogTitle>
          <DialogDescription>
            Connect your Zalo account to send messages to landlords directly from the app.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Connection Status */}
          <div className="flex items-center gap-3 p-3 rounded-lg border">
            {isConnected ? (
              <Wifi className="h-5 w-5 text-green-500" />
            ) : (
              <WifiOff className="h-5 w-5 text-muted-foreground" />
            )}
            <div className="flex-1">
              <p className="text-sm font-medium">
                {isConnected ? "Connected" : "Not connected"}
              </p>
              {isConnected && status?.phone_number && (
                <p className="text-xs text-muted-foreground">
                  Phone: {status.phone_number}
                </p>
              )}
            </div>
            {isConnected && (
              <span className="h-2 w-2 rounded-full bg-green-500" />
            )}
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {isConnected ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Your Zalo account is connected. You can send messages to landlords from listing details.
              </p>
              <Button
                variant="outline"
                onClick={handleDisconnect}
                disabled={connecting}
                className="w-full"
              >
                {connecting ? "Disconnecting..." : "Disconnect"}
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="cookie">Zalo Cookie</Label>
                  <Textarea
                    id="cookie"
                    value={cookie}
                    onChange={(e) => setCookie(e.target.value)}
                    placeholder='{"zpw_sek": "...", "zpw_uid": "...", ...}'
                    className="font-mono text-xs h-[100px] min-h-[100px] max-h-[100px] overflow-auto resize-none break-all"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="imei">IMEI</Label>
                  <Input
                    id="imei"
                    value={imei}
                    onChange={(e) => setImei(e.target.value)}
                    placeholder="Enter IMEI from DevTools"
                    className="font-mono text-xs"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="userAgent">User Agent</Label>
                  <Input
                    id="userAgent"
                    value={userAgent}
                    onChange={(e) => setUserAgent(e.target.value)}
                    placeholder="Mozilla/5.0..."
                    className="font-mono text-xs"
                  />
                </div>
              </div>

              <div className="rounded-lg bg-muted/50 p-3">
                <p className="text-xs font-medium mb-2">How to get login info:</p>
                <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
                  <li>Open chat.zalo.me in Chrome</li>
                  <li>Press F12 to open DevTools</li>
                  <li>Select Application tab → Cookies</li>
                  <li>Copy all cookies as JSON</li>
                  <li>IMEI can be found in Network tab when sending a message</li>
                </ol>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            {isConnected ? "Close" : "Cancel"}
          </Button>
          {!isConnected && (
            <Button
              onClick={handleConnect}
              disabled={connecting || !cookie.trim() || !imei.trim()}
            >
              {connecting ? "Connecting..." : "Connect"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
