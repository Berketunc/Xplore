import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

export function InteractiveWorkspace() {
  const frame = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(820);
  useEffect(() => {
    if (!api.baseUrl || api.mode !== "live") return;
    const origin = new URL(api.baseUrl, window.location.href).origin;
    const resize = (event: MessageEvent) => {
      if (event.origin !== origin || event.source !== frame.current?.contentWindow) return;
      if (event.data?.type === "xplore-workspace-resize" && Number.isFinite(event.data.height)) {
        setHeight(Math.max(590, Math.min(1800, Math.ceil(event.data.height))));
      }
    };
    window.addEventListener("message", resize);
    return () => window.removeEventListener("message", resize);
  }, []);
  if (api.mode !== "live" || !api.baseUrl) {
    return <div className="rounded-xl border border-hairline bg-surface p-6 text-sm text-ink-2">The interactive workspace uses the live physics API. Set VITE_API_MODE=live and the backend URL to enable grabbing and deformation.</div>;
  }
  return <iframe ref={frame} title="Xplore gripper pad experiment workspace" src={`${api.baseUrl.replace(/\/$/, "")}/sandbox?workspace=robotics-v1`} style={{ height }} className="w-full rounded-xl border border-hairline bg-surface" allow="fullscreen" />;
}
