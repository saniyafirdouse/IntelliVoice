import { Link } from "react-router-dom";
import { Icon } from "../components/Icon";
import { PageShell } from "../components/PageShell";

export default function NotFoundPage() {
  return (
    <PageShell scope="pg-404" variant="app" title="Page not found" className="bg-background">
      <main className="min-h-[70vh] pt-32 px-margin-mobile flex flex-col items-center justify-center text-center gap-4">
        <Icon name="explore_off" className="text-[48px] text-secondary" />
        <h1 className="font-headline-md text-headline-md text-white">This page doesn&apos;t exist</h1>
        <p className="text-white/80">The link may be broken, or the page may have moved.</p>
        <div className="flex gap-3">
          <Link to="/" className="px-5 py-2.5 rounded-full text-white font-semibold border border-white/30 bg-white/10 hover:bg-white/20">Home</Link>
          <Link to="/chat" className="px-5 py-2.5 rounded-full text-white font-semibold" style={{ background: "rgb(88, 92, 176)" }}>Ask IntelliVoice</Link>
        </div>
      </main>
    </PageShell>
  );
}
