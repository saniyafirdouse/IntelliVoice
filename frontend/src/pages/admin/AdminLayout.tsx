import { useEffect } from "react";
import { Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { PageShell } from "../../components/PageShell";
import { useAuth } from "../../context/AuthContext";
import { setUnauthorizedHandler } from "../../lib/adminApi";
import { ACCENT, GLASS_PANEL, glassCard } from "./AdminUi";

const SECTIONS = [
  { to: "/admin", end: true, label: "Dashboard", icon: "monitoring", hint: "What parents ask" },
  { to: "/admin/data", label: "Update Data", icon: "upload_file", hint: "Excel upload" },
  { to: "/admin/history", label: "Upload History", icon: "history", hint: "Undo changes" },
  { to: "/admin/unanswered", label: "Unanswered", icon: "help_center", hint: "Missing data" },
];

/** Frame for every admin page: only admins get in; everyone else is sent to sign in. */
export default function AdminLayout() {
  const { user, token, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // If the login expires while the admin is working, go back to the sign-in page.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      logout();
      navigate("/login?role=admin", { replace: true });
    });
    return () => setUnauthorizedHandler(() => {});
  }, [logout, navigate]);

  if (!user || !token || user.role !== "admin") {
    return <Navigate to={`/login?role=admin&next=${encodeURIComponent(location.pathname)}`} replace />;
  }

  return (
    <PageShell scope="pg-admin" variant="app" title="Admin Panel" className="bg-background font-body-md text-on-surface antialiased">
      <div className="fixed inset-0 z-0 pointer-events-none bg-cover bg-center" style={{ backgroundImage: 'url("/assets/campus-sunset.jpg")' }} aria-hidden="true">
        {/* same light veil as the Voice Chat page so the campus photo shows through the glass */}
        <div className="absolute inset-0 bg-black/15" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60" />
      </div>

      <div className="relative z-10 w-full max-w-[1400px] mx-auto px-margin-mobile lg:px-margin pt-28 pb-12 flex flex-col lg:flex-row gap-space-lg">
        {/* side navigation (top tabs on small screens) */}
        <aside className="lg:w-60 flex-shrink-0">
          <div className={`${GLASS_PANEL} p-space-md lg:sticky lg:top-28 flex flex-col gap-space-sm`} style={glassCard}>
            <div className="hidden lg:flex items-center gap-2 px-2 pt-1 pb-3 border-b border-white/15">
              <Icon name="admin_panel_settings" className="text-[20px] text-secondary font-bold flex-shrink-0" />
              <div className="flex flex-col min-w-0">
                <span className="font-title-md text-title-md text-white font-bold">Admin Panel</span>
                <span className="font-body-sm text-body-sm text-white/70 truncate" title={user.email}>{user.email}</span>
              </div>
            </div>
            <nav aria-label="Admin" className="flex lg:flex-col gap-1 overflow-x-auto">
              {SECTIONS.map((s) => (
                <NavLink
                  key={s.to}
                  to={s.to}
                  end={s.end}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 px-4 py-2 rounded-full whitespace-nowrap border transition-colors ${isActive ? "text-white shadow-[0_4px_14px_rgba(0,0,0,0.35)]" : "text-white/80 border-transparent hover:text-white hover:bg-white/10"}`}
                  style={({ isActive }) => (isActive ? { backgroundColor: ACCENT, borderColor: "rgba(255,255,255,0.35)" } : undefined)}
                >
                  <Icon name={s.icon} className="text-[20px]" />
                  <span className="flex flex-col leading-tight">
                    <span className="font-label-lg text-label-lg font-semibold">{s.label}</span>
                    <span className="hidden lg:block font-body-sm text-[11px] text-white/70">{s.hint}</span>
                  </span>
                </NavLink>
              ))}
            </nav>
          </div>
        </aside>

        <main className="flex-1 min-w-0 flex flex-col gap-space-lg">
          <Outlet />
        </main>
      </div>
    </PageShell>
  );
}
