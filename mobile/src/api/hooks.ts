import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

export interface Category {
  id: number;
  name: string;
  parent: number | null;
  kind: "INCOME" | "EXPENSE";
}

export interface FinancialAccount {
  id: number;
  name: string;
  account_type: string;
  currency: string;
}

export interface Transaction {
  id: number;
  account: number;
  account_name: string;
  category: number | null;
  category_name: string | null;
  amount: string;
  date: string;
  merchant: string;
  description: string;
  source: string;
  external_id: string | null;
  is_recurring: boolean;
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Budget {
  id: number;
  category: number;
  category_name: string;
  monthly_limit: string;
}

export interface DashboardSummary {
  year: number;
  month: number;
  total_spent: number | string;
  by_category: Array<{
    category__name: string;
    total: number | string;
  }>;
}

export interface AdviceMessage {
  id: number;
  insight: number;
  body: string;
  model_used: string;
  user_feedback: string | null;
  created_at: string;
}

export interface Insight {
  id: number;
  rule_key: string;
  severity: "INFO" | "WARNING" | "CRITICAL";
  category: number | null;
  period_start: string;
  period_end: string;
  summary: string;
  raw_data: Record<string, any>;
  created_at: string;
  advice: AdviceMessage[];
}

export interface MetalRates {
  gold: Record<string, number>;
  silver: Record<string, number>;
  platinum: Record<string, number>;
  last_updated: string | null;
}

// 1. Transactions hook - CRITICAL: Reads response.results from DRF pagination envelope
export function useTransactions(page: number = 1, categoryId?: number) {
  return useQuery({
    queryKey: ["transactions", page, categoryId],
    queryFn: async () => {
      const params = new URLSearchParams({ page: page.toString() });
      if (categoryId) {
        params.append("category", categoryId.toString());
      }
      const response = await api.get<PaginatedResponse<Transaction>>(
        `/transactions/?${params.toString()}`
      );
      return response.results;
    },
  });
}

// 2. Create Transaction mutation with cache invalidation
export function useCreateTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: {
      account: number;
      category?: number | null;
      amount: string | number;
      date: string;
      merchant: string;
      description?: string;
    }) => api.post<Transaction>("/transactions/", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
    },
  });
}

// 3. Dashboard Summary hook
export function useDashboardSummary(year?: number, month?: number) {
  return useQuery({
    queryKey: ["dashboard", year, month],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (year) params.append("year", year.toString());
      if (month) params.append("month", month.toString());
      const queryStr = params.toString() ? `?${params.toString()}` : "";
      return await api.get<DashboardSummary>(`/dashboard/summary/${queryStr}`);
    },
  });
}

// 4. Budgets hook (ModelViewSet is paginated)
export function useBudgets() {
  return useQuery({
    queryKey: ["budgets"],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<Budget>>("/budgets/");
      return response.results || [];
    },
  });
}

// 5. Advisor Feed hook (unpaginated)
export function useAdvisorFeed() {
  return useQuery({
    queryKey: ["advisor"],
    queryFn: async () => {
      return await api.get<Insight[]>("/advisor/feed/");
    },
  });
}

// 6. Advisor Refresh mutation
export function useRefreshAdvisor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<Insight[]>("/advisor/refresh/"),
    onSuccess: (data) => {
      queryClient.setQueryData(["advisor"], data);
      queryClient.invalidateQueries({ queryKey: ["advisor"] });
    },
  });
}

// 7. Metal Rates hook (unpaginated, AllowAny, 5-minute refetch interval)
export function useMetalRates() {
  return useQuery({
    queryKey: ["rates"],
    queryFn: async () => {
      return await api.get<MetalRates>("/rates/");
    },
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  });
}

// 8. Categories and Financial Accounts hooks
export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<Category>>("/categories/");
      return response.results || [];
    },
  });
}

export function useAccounts() {
  return useQuery({
    queryKey: ["accounts"],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<FinancialAccount>>("/accounts/");
      return response.results || [];
    },
  });
}
