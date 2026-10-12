import { lazy, Suspense, useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import HomePage from "./pages/HomePage";

// Pages other than Home are loaded on demand to keep the first load small.
const ChatPage = lazy(() => import("./pages/chat/ChatPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));
const FaqPage = lazy(() => import("./pages/FaqPage"));
const LoginPage = lazy(() => import("./pages/auth/LoginPage"));
const SignupPage = lazy(() => import("./pages/auth/SignupPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
// Admin panel (only admins can open these; others are sent to sign in)
const AdminLayout = lazy(() => import("./pages/admin/AdminLayout"));
const AdminDashboardPage = lazy(() => import("./pages/admin/AdminDashboardPage"));
const AdminDataPage = lazy(() => import("./pages/admin/AdminDataPage"));
const AdminHistoryPage = lazy(() => import("./pages/admin/AdminHistoryPage"));
const AdminUnansweredPage = lazy(() => import("./pages/admin/AdminUnansweredPage"));

/** Scroll to the top on page change (but keep #section links working). */
function ScrollToTop() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (!hash) window.scrollTo(0, 0);
  }, [pathname, hash]);
  return null;
}

function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-white/80" role="status">
      <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
      Loading…
    </div>
  );
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/help" element={<FaqPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboardPage />} />
            <Route path="data" element={<AdminDataPage />} />
            <Route path="history" element={<AdminHistoryPage />} />
            <Route path="unanswered" element={<AdminUnansweredPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </>
  );
}
