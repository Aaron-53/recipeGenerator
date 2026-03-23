import { TailChase } from "ldrs/react";
import "ldrs/react/TailChase.css";

export function LoaderSpinner({ size = "md", className = "", color }) {
  const sizeMap = { xs: "20", sm: "28", md: "40", lg: "56" };
  const px = sizeMap[size] ?? sizeMap.md;
  const resolvedColor =
    color ??
    (size === "xs" || size === "sm" ? "black" : "#F2CEC2");

  return (
    <div className={`inline-flex items-center justify-center ${className}`} aria-hidden>
      <TailChase size={px} speed="1.75" color={resolvedColor} />
    </div>
  );
}

export default function Loader({ fullscreen = false, className = "" }) {
  const inner = <LoaderSpinner size="md" />;

  if (fullscreen) {
    return (
      <div
        className={`fixed inset-0 z-50 flex items-center justify-center bg-[#5b6d44]/90 ${className}`}
        role="status"
        aria-label="Loading"
      >
        {inner}
      </div>
    );
  }

  return (
    <div
      className={`flex w-full flex-1 items-center justify-center py-16 min-h-48 ${className}`}
      role="status"
      aria-label="Loading"
    >
      {inner}
    </div>
  );
}
