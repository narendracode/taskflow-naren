import { Link, useNavigate } from "react-router-dom";
import { LogOutIcon, LayoutDashboardIcon } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/app/store";
import { logout } from "@/features/auth/authSlice";
import { Button } from "./ui/button";
import { initials } from "@/lib/utils";

export function Navbar() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const user = useAppSelector((s) => s.auth.user);

  const handleLogout = () => {
    dispatch(logout());
    navigate("/login");
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
          <div className="flex items-center gap-3">
            {/* Avatar */}
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                {initials(user.name)}
              </span>
              <span className="hidden text-sm font-medium sm:block">
                {user.name}
              </span>
            </div>

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
