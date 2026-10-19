"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApprovalDetailCard, BackToTrades } from "@/components/options/ApprovalDetail";
import type { ApprovalDetail } from "@/components/options/types";
import { ApiError, apiFetch } from "@/lib/api";

const SHELL = "mx-auto max-w-[1200px] px-4 py-3 md:px-7 md:py-4";

export default function ApprovalDetailPage({ params }: { params: Promise<{ approvalId: string }> }) {
  const { approvalId } = use(params);
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["options", "approval", approvalId],
    queryFn: () => apiFetch<ApprovalDetail>(`/options/approvals/${approvalId}`),
    // A 404 will not change on a retry; anything else is worth one more try.
    retry: (n, e) => !(e instanceof ApiError && e.status === 404) && n < 1,
  });

  if (isLoading) {
    return (
      <div className={SHELL}>
        <BackToTrades />
        <div role="status" aria-busy="true" aria-label="Loading the proposal">
          <div className="mt-2 h-8 w-64 rounded-xl bg-sunk" />
          <div className="mt-4 h-64 rounded-[18px] bg-surface" />
        </div>
      </div>
    );
  }
  if (isError || !data) {
    const missing = error instanceof ApiError && error.status === 404;
    return (
      <div className={SHELL}>
        <BackToTrades />
        <h1 className="mt-2 text-2xl font-extrabold tracking-[-0.015em]">{missing ? "Not found" : "Not loaded"}</h1>
        <p className="mt-3 text-sm">
          {missing
            ? "This proposal does not exist or has been pruned."
            : "This proposal could not be loaded. Go back and open it again in a moment."}
        </p>
      </div>
    );
  }
  return (
    <div className={SHELL}>
      <ApprovalDetailCard detail={data} />
    </div>
  );
}
