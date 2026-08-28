import { MiniHeader } from "@/components/MiniHeader";
import { MiniTabBar } from "@/components/MiniTabBar";

export default function MiniLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mini-shell">
      <MiniHeader />
      {children}
      <MiniTabBar />
    </div>
  );
}
