import { useMemo, useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useNavigate, useLocation } from "react-router-dom";
import { RxHamburgerMenu } from "react-icons/rx";
import { IoCloseOutline } from "react-icons/io5";
import { useAuth } from "../context/AuthContext";
import { motion as Motion } from "framer-motion";
import { useBodyScrollLock } from "../hooks/useBodyScrollLock";

const NAV_LINKS = [
  { label: "Edit inventory", to: "/inventory" },
  { label: "Generate recipe", to: "/generate-recipe" },
  { label: "Browse recipes", to: "/browse-recipes" },
];

export default function Navbar() {
  const { logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const items = useMemo(() => {
    const links = NAV_LINKS.map((l) => ({ type: "link", ...l }));
    if (isAuthenticated) return [...links, { type: "logout", label: "Logout" }];
    return [
      ...links,
      {
        type: "link",
        label: "Login",
        to: "/signin",
        matchPaths: ["/signin", "/signup"],
      },
    ];
  }, [isAuthenticated]);

  useBodyScrollLock(mobileNavOpen);

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
    setMobileNavOpen(false);
  };

  useEffect(() => {
    const id = window.setTimeout(() => setMobileNavOpen(false), 0);
    return () => clearTimeout(id);
  }, [pathname]);

  const runMobileItem = (item) => {
    if (item.type === "logout") {
      void onLogout();
      return;
    }
    navigate(item.to);
    setMobileNavOpen(false);
  };

  const mobileChrome =
    typeof document !== "undefined"
      ? createPortal(
          <div className="lg:hidden">
            <div
              className="pointer-events-none fixed inset-x-0 top-0 z-[10050] flex justify-end"
              style={{ padding: "24px 16px 16px 16px" }}
            >
              <button
                type="button"
                className="pointer-events-auto cursor-pointer flex items-center justify-center rounded-lg p-1 text-[#f5e8c7] outline-none focus-visible:ring-2 focus-visible:ring-[#f5e8c7]/50"
                aria-expanded={mobileNavOpen}
                aria-label={mobileNavOpen ? "Close menu" : "Open menu"}
                onClick={() => setMobileNavOpen((o) => !o)}
              >
                {mobileNavOpen ? (
                  <IoCloseOutline className="h-10 w-10" aria-hidden />
                ) : (
                  <RxHamburgerMenu className="h-10 w-10" aria-hidden />
                )}
              </button>
            </div>

            <div
              className={`fixed inset-0 z-[10040] flex flex-col items-center justify-center bg-[#3d4a2e]/92 backdrop-blur-md transition-[opacity,visibility] duration-300 ease-in-out ${
                mobileNavOpen ? "visible opacity-100" : "invisible pointer-events-none opacity-0"
              }`}
              aria-hidden={!mobileNavOpen}
            >
              <nav className="flex w-full max-w-sm flex-col items-stretch gap-6 px-8" aria-label="Main">
                {items.map((item) => {
                  const isActive = activeLabel === item.label;
                  return (
                    <button
                      key={item.label}
                      type="button"
                      onClick={() => runMobileItem(item)}
                      className={`px-1 py-5 text-center cursor-pointer text-xl font-semibold transition-colors ${
                        isActive
                          ? "text-[#E69695]"
                          : "text-[#F6E7C8]/50 hover:text-[#F6E7C8]/75"
                      }`}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </nav>
            </div>
          </div>,
          document.body
        )
      : null;

  return (
    <>
      <header className="relative w-full">
        <div
          className="hidden w-full lg:flex lg:justify-center"
          style={{ padding: "24px 16px 32px 16px" }}
        >
          <nav
            style={{
              position: "relative",
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              backgroundColor: "#F6E7C8",
              borderRadius: 999,
              padding: "5px",
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
                    <Motion.span
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
        </div>
      </header>
      {mobileChrome}
    </>
  );
}
