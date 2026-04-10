import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { Navbar } from "@/components/Navbar";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ProjectsPage } from "@/pages/ProjectsPage";
import { ProjectDetailPage } from "@/pages/ProjectDetailPage";
import { useAppDispatch, useAppSelector } from "@/app/store";
import { setCredentials } from "@/features/auth/authSlice";
import { useGetMeQuery } from "@/features/users/usersApi";

/**
 * Fetches the freshest user profile (including theme) from the server once
 * after login. Handles the cross-device case: if the user changed their
 * theme on another device, this sync picks it up on the next session start.
 */
function ThemeSync() {
  const dispatch = useAppDispatch();
  const isAuthenticated = useAppSelector((s) => s.auth.isAuthenticated);
  const token = useAppSelector((s) => s.auth.token);

  const { data: freshUser } = useGetMeQuery(undefined, {
    skip: !isAuthenticated,
  });

  useEffect(() => {
    if (freshUser && token) {
      dispatch(setCredentials({ user: freshUser, token }));
    }
  }, [freshUser, token, dispatch]);

  return null;
}

/** Shared shell for authenticated pages: navbar + main content area */
function AuthLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      {/* ThemeSync runs globally — it is a no-op when unauthenticated */}
      <ThemeSync />
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* Protected — guard first, then render layout shell */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AuthLayout />}>
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/:id" element={<ProjectDetailPage />} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/projects" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
