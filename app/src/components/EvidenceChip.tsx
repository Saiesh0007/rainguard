import { EVIDENCE, type EvidenceKind } from "../lib/labels";

const ICON: Record<EvidenceKind, string> = {
  observed: "●",
  historical: "◷",
  estimated: "≈",
  forecast: "↗",
  unknown: "?",
};

export default function EvidenceChip({ kind }: { kind: EvidenceKind }) {
  const e = EVIDENCE[kind];
  return (
    <span className={`chip chip--${kind}`} title={e.help}>
      <span aria-hidden="true">{ICON[kind]}</span> {e.label}
    </span>
  );
}
