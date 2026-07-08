import type { ReactNode } from "react";

export type InfoKind = "info" | "success" | "error" | "warning";

interface Props {
  kind: InfoKind;
  children: ReactNode;
}

/** Caja de estado bajo cada sección (usa las clases .info-box de styles.css). */
export function InfoBox({ kind, children }: Props) {
  return <div className={`info-box ${kind}`}>{children}</div>;
}
