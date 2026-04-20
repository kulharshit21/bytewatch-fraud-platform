import Link from "next/link";
import { Activity, BarChart3, Blocks, ShieldCheck, Siren } from "lucide-react";

import { Badge } from "@/components/ui/badge";

const navItems = [
  { href: "/overview", label: "Overview", icon: Activity },
  { href: "/cases", label: "Cases", icon: Siren },
  { href: "/models", label: "Models", icon: Blocks },
  { href: "/monitoring", label: "Monitoring", icon: BarChart3 },
];

export function ConsoleShell({
  section,
  title,
  subtitle,
  children,
}: {
  section: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(79,195,161,0.12),transparent_22%),linear-gradient(180deg,#07111f_0%,#091322_42%,#050b14_100%)] px-4 py-4 text-foreground sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[240px,1fr]">
        <aside className="rounded-[28px] border border-border/80 bg-panel/80 p-5 shadow-panel">
          <div className="flex items-center gap-3 border-b border-border/70 pb-5">
            <div className="rounded-2xl border border-accent/30 bg-accent/10 p-3 text-accent">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted">Fraud Ops</p>
              <p className="text-base font-semibold">Live Analyst Console</p>
            </div>
          </div>

          <nav className="mt-5 space-y-2">
            {navItems.map(({ href, label, icon: Icon }) => {
              const active = section === href.replace("/", "");
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition-colors ${
                    active
                      ? "border border-accent/30 bg-accent/10 text-foreground"
                      : "border border-transparent text-muted hover:border-border hover:bg-panelMuted/60 hover:text-foreground"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="mt-8 rounded-2xl border border-border bg-panelMuted/45 p-4">
            <Badge variant="neutral" className="mb-3 w-fit">
              Runtime
            </Badge>
            <p className="text-sm leading-6 text-muted">
              Dashboard values are fetched live from the FastAPI service. Empty states stay honest until the
              producer and worker generate real cases.
            </p>
          </div>
        </aside>

        <section className="space-y-6">
          <header className="rounded-[28px] border border-border/70 bg-panel/60 p-6 shadow-panel">
            <Badge variant="neutral" className="mb-4 w-fit">
              Production Demo
            </Badge>
            <div className="space-y-3">
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{title}</h1>
              <p className="max-w-3xl text-sm leading-6 text-muted">{subtitle}</p>
            </div>
          </header>

          {children}
        </section>
      </div>
    </main>
  );
}
