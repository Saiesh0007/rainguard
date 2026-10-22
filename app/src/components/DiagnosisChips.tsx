import type { DiagnosisId, DiagnosisLabel } from "../types";

/** Rule-based labels (analysis/diagnose.py) as text pills; the rule is in the tooltip. */
export default function DiagnosisChips({ ids, labels }: { ids: DiagnosisId[]; labels: Record<DiagnosisId, DiagnosisLabel> }) {
  if (ids.length === 0) return null;
  return (
    <span className="dx-list">
      {ids.map((d) => <span key={d} className={`dx dx--${d}`} title={labels[d].rule}>{labels[d].title}</span>)}
    </span>
  );
}
