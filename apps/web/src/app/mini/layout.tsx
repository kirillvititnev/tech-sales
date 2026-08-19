import { MiniHeader } from "@/components/MiniHeader";

export default function MiniLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mini-shell">
      <MiniHeader />
      {children}
    </div>
  );
}
