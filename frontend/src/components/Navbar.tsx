import { Link, useNavigate } from "react-router-dom";
import { LogOutIcon, LayoutDashboardIcon, SunIcon, MoonIcon } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/app/store";
import { logout, setCredentials } from "@/features/auth/authSlice";
import { useUpdatePreferencesMutation } from "@/features/users/usersApi";
import { Button } from "./ui/button";
import { initials } from "@/lib/utils";

export function Navbar() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const user = useAppSelector((s) => s.auth.user);
  const token = useAppSelector((s) => s.auth.token);

  const [updatePreferences, { isLoading: savingTheme }] =
    useUpdatePreferencesMutation();

  const handleLogout = () => {
    dispatch(logout());
    navigate("/login");
  };

  const handleThemeToggle = async () => {
    if (!user || !token) return;
    const newTheme = user.theme === "dark" ? "light" : "dark";
    try {
      const updated = await updatePreferences({ theme: newTheme }).unwrap();
      // Sync updated user (with persisted theme) back into the store + localStorage
      dispatch(setCredentials({ user: updated, token }));
    } catch {
      // toggle reverts automatically since state wasn't mutated on error
    }
  };

  return (
    <header className="sticky top-0 z-40 border-b bg-background">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Logo */}
        <Link
          to="/projects"
          className="flex items-center gap-2 font-semibold text-primary"
        >
          <LayoutDashboardIcon className="h-5 w-5" />
          <span>TaskFlow</span>
        </Link>

        {/* User area */}
        {user && (
          <div className="flex items-center gap-2">
            {/* Avatar + name */}
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                {initials(user.name)}
              </span>
              <span className="hidden text-sm font-medium sm:block">
                {user.name}
              </span>
            </div>

            {/* Dark / light toggle */}
            <Button
              variant="ghost"
              size="icon"
              onClick={handleThemeToggle}
              disabled={savingTheme}
              title={user.theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {user.theme === "dark" ? (
                <SunIcon className="h-4 w-4" />
              ) : (
                <MoonIcon className="h-4 w-4" />
              )}
            </Button>

            {/* Logout */}
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              title="Logout"
            >
              <LogOutIcon className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
