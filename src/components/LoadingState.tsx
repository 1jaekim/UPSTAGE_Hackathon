import { Loader2 } from "lucide-react";

export default function LoadingState() {
  return (
    <div className="h-full flex flex-col items-center justify-center gap-4 p-6">
      <Loader2 className="w-8 h-8 text-brand animate-spin" />
      <div className="text-center">
        <p className="text-sm font-semibold text-brand-dark">검증 진행 중</p>
        <p className="text-[10px] text-slate-400 mt-1">Multi-Agent 협업 중...</p>
      </div>
    </div>
  );
}
