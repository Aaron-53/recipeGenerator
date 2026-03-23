import { useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { motion } from "framer-motion";

const NAV_ITEMS = ["Home", "Edit inventory", "Generate recipe", "Logout"];

export default function Navbar() {
  const { logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const items = useMemo(() => {
    return NAV_ITEMS.map((name) => {
      if (name === "Home") return { type: "link", label: "Home", to: "/home" };
      if (name === "Edit inventory") return { type: "link", label: "Edit inventory", to: "/inventory" };
      if (name === "Generate recipe") return { type: "link", label: "Generate recipe", to: "/generate-recipe" };
      if (isAuthenticated) return { type: "logout", label: "Logout" };
      return { type: "link", label: "Login", to: "/signin", matchPaths: ["/signin", "/signup"] };
    });
  }, [isAuthenticated]);

  const activeLabel = useMemo(() => {
    for (const item of items) {
      if (item.type === "logout") continue;
      if (item.matchPaths?.includes(pathname)) return item.label;
      if (pathname === item.to) return item.label;
      if (item.to && item.to !== "/" && pathname.startsWith(item.to)) return item.label;
    }
    return null;
  }, [pathname, items]);

  const onLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <header style={{ display: "flex", width: "100%", justifyContent: "center", padding: "24px 16px 32px 16px" }}>
      <nav
        style={{
          position: "relative",
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
          backgroundColor: "#F6E7C8",
          borderRadius: 999,
          padding: "5px 12px",
        }}
      >
        {items.map((item) => {
          const isActive = activeLabel === item.label;
          const onClick = item.type === "logout" ? onLogout : () => navigate(item.to);

          return (
            <button
              key={item.label}
              type="button"
              onClick={onClick}
              aria-current={isActive ? "page" : undefined}
              style={{
                position: "relative",
                zIndex: 1,
                background: "transparent",
                border: "none",
                borderRadius: 999,
                padding: "9px 22px",
                fontSize: 15,
                fontWeight: 450,
                color: "#000000",
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "color 0.2s",
              }}
            >
              {isActive && (
                <motion.span
                  layoutId="navbar-pill"
                  style={{
                    position: "absolute",
                    inset: 0,
                    backgroundColor: "#E69695",
                    borderRadius: 999,
                    zIndex: -1,
                  }}
                  transition={{ type: "spring", stiffness: 400, damping: 35 }}
                />
              )}
              {item.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}