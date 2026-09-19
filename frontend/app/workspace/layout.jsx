import Navbar from "@/components/Navbar";

export default function WorkspaceLayout({ children }) {
  return (
    <div className="flex h-screen bg-bg">
      <Navbar />
      <main className="h-screen flex-1 overflow-y-auto px-8 py-8">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}
