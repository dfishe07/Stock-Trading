import { ReactNode } from "react";

interface CardProps {
  title?: string;
  subtitle?: string;
  children: ReactNode;
}

export function Card({ title, subtitle, children }: CardProps) {
  return (
    <section className="card">
      {title ? <h3>{title}</h3> : null}
      {subtitle ? <p className="card-subtitle">{subtitle}</p> : null}
      {children}
    </section>
  );
}

