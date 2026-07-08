import type { ReactNode } from "react";

interface Props {
  step: number;
  title: string;
  desc?: string;
  children: ReactNode;
}

/** Card de sección con eyebrow numerado — el flujo de la app es secuencial. */
export function Section({ step, title, desc, children }: Props) {
  return (
    <section className="card">
      <div className="step-label">
        Paso <span className="step-num">{String(step).padStart(2, "0")}</span>
      </div>
      <h2>{title}</h2>
      {desc && <p className="section-desc">{desc}</p>}
      {children}
    </section>
  );
}
