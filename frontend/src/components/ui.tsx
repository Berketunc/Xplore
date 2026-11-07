import type { ReactNode } from "react";
import type { EvidenceStatus, Outcome } from "../types/contract";
import { EVIDENCE_LABEL } from "../lib/format";

export function Card({ title, aside, children, className = "" }: { title?: ReactNode; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-hairline bg-surface p-5 ${className}`}>
      {(title || aside) && (
        <header className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          {title && <h2 className="text-sm font-semibold text-ink">{title}</h2>}
          {aside && <div className="text-xs text-ink-2">{aside}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Pill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "warning" | "good" | "critical" }) {
  const toneClass = {
    neutral: "bg-surface-2 text-ink-2",
    warning: "bg-warning/20 text-ink",
    good: "bg-good/15 text-ink",
    critical: "bg-critical/15 text-ink",
  }[tone];
  return <span className={`inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${toneClass}`}>{children}</span>;
}

/** Line key in the series colour: identity sits beside the text, never on it. */
export function SeriesKey({ color, className = "" }: { color: string; className?: string }) {
  return <span aria-hidden className={`inline-block h-0.5 w-4 shrink-0 rounded-full ${className}`} style={{ background: color, height: 3 }} />;
}

export function OutcomeBadge({ outcome }: { outcome: Outcome | null }) {
  if (outcome === "meets_target") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ink">
        <svg viewBox="0 0 16 16" className="h-4 w-4 text-good" aria-hidden>
          <circle cx="8" cy="8" r="8" fill="currentColor" />
          <path d="M4.5 8.2l2.2 2.2 4.8-4.8" stroke="#fff" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Meets target
      </span>
    );
  }
  if (outcome === "exceeds_target") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-ink">
        <svg viewBox="0 0 16 16" className="h-4 w-4 text-critical" aria-hidden>
          <circle cx="8" cy="8" r="8" fill="currentColor" />
          <path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
        Exceeds target
      </span>
    );
  }
  return <span className="text-xs text-ink-muted">Not evaluated</span>;
}

export function EvidenceBadge({ status, fixture }: { status: EvidenceStatus; fixture?: boolean }) {
  const illustrative = status === "illustrative" || fixture;
  return (
    <Pill tone={illustrative ? "warning" : status === "physically_compared" ? "good" : "neutral"}>
      {illustrative && <span aria-hidden>⚠</span>}
      {EVIDENCE_LABEL[illustrative ? "illustrative" : status]}
    </Pill>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={`h-3.5 w-3.5 animate-spin ${className}`} aria-hidden>
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2" fill="none" />
      <path d="M14 8a6 6 0 0 0-6-6" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" />
    </svg>
  );
}
