import { useEffect, type CSSProperties, type ReactNode } from "react";
import { SiteFooter } from "./SiteFooter";
import { SiteHeader, type HeaderVariant } from "./SiteHeader";

interface PageShellProps {
  /** CSS scope class for this page's own styles, e.g. "pg-home" (see src/styles). */
  scope: string;
  variant: HeaderVariant;
  title: string;
  className?: string;
  style?: CSSProperties;
  /** Elements that sit behind/around the page (backgrounds, floating buttons). */
  before?: ReactNode;
  after?: ReactNode;
  children: ReactNode;
}

/** Common page frame: header + page content + footer, with the page's scoped style class. */
export function PageShell({ scope, variant, title, className = "", style, before, after, children }: PageShellProps) {
  useEffect(() => {
    document.title = `${title} · IntelliVoice`;
  }, [title]);

  return (
    <div className={`${scope} min-h-screen ${className}`} style={style}>
      {before}
      <SiteHeader variant={variant} />
      {children}
      {after}
      <SiteFooter variant={variant} />
    </div>
  );
}
