import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAppSelector } from "@/app/store";

/** Wraps routes that require authentication. Redirects to /login if not authenticated. */
export function ProtectedRoute() {
  const isAuthenticated = useAppSelector((s) => s.auth.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}
