import type { ReactNode } from "react";

interface Props {
  step: number;
  title: string;
  desc?: string;
  children: ReactNode;
}

/** Card de sección con eyebrow numerado — el flujo de la app es secuencial. */
export function Section({ step, title, desc, children }: Props) {
  const num = String(step).padStart(2, "0");

  return (
    <section className="card">
      <span className="ghost-num" aria-hidden="true">
        {num}
      </span>
      <div className="step-label">
        Paso <span className="step-num">{num}</span>
      </div>
      <h2>{title}</h2>
      {desc && <p className="section-desc">{desc}</p>}
      {children}
    </section>
  );
}
