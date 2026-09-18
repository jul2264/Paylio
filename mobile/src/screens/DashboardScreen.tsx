import React from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useDashboardSummary } from "../api/hooks";

export default function DashboardScreen() {
  const { data: summary, isLoading, refetch, isRefetching } = useDashboardSummary();

  if (isLoading && !summary) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#10b981" />
      </View>
    );
  }

  const totalSpent = summary?.total_spent ?? "0.00";
  const formattedTotal = Number(totalSpent).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const categories = summary?.by_category || [];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={isRefetching}
          onRefresh={refetch}
          tintColor="#10b981"
        />
      }
    >
      {/* Header Greeting */}
      <View style={styles.header}>
        <Text style={styles.greeting}>Welcome back</Text>
        <Text style={styles.title}>Monthly Overview</Text>
      </View>

      {/* Main KPI Card */}
      <View style={styles.kpiCard}>
        <Text style={styles.kpiLabel}>Total Spending This Month</Text>
        <Text style={styles.kpiValue} testID="total-spent-value">
          ₹{formattedTotal}
        </Text>
        <Text style={styles.kpiSub}>Across all accounts & categories</Text>
      </View>

      {/* Category Breakdown */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Spending by Category</Text>
      </View>

      {categories.length === 0 ? (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>No spending recorded this month yet.</Text>
        </View>
      ) : (
        categories.map((cat, index) => {
          const amount = Number(cat.total).toLocaleString("en-IN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          });
          return (
            <View key={cat.category__name || index} style={styles.categoryCard}>
              <View style={styles.categoryInfo}>
                <Text style={styles.categoryName}>
                  {cat.category__name || "Uncategorized"}
                </Text>
              </View>
              <Text style={styles.categoryAmount}>₹{amount}</Text>
            </View>
          );
        })
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#090d16",
  },
  content: {
    padding: 20,
    paddingBottom: 40,
  },
  centerContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#090d16",
  },
  header: {
    marginBottom: 20,
    marginTop: 10,
  },
  greeting: {
    fontSize: 14,
    color: "#94a3b8",
    fontWeight: "500",
  },
  title: {
    fontSize: 26,
    color: "#f8fafc",
    fontWeight: "800",
    letterSpacing: 0.5,
  },
  kpiCard: {
    backgroundColor: "#131b2e",
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: "#1e293b",
    marginBottom: 24,
    shadowColor: "#10b981",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 16,
  },
  kpiLabel: {
    fontSize: 13,
    color: "#94a3b8",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  kpiValue: {
    fontSize: 34,
    color: "#10b981",
    fontWeight: "900",
    marginTop: 8,
    marginBottom: 4,
  },
  kpiSub: {
    fontSize: 12,
    color: "#64748b",
  },
  sectionHeader: {
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#e2e8f0",
  },
  emptyCard: {
    backgroundColor: "#131b2e",
    padding: 20,
    borderRadius: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  emptyText: {
    color: "#64748b",
    fontSize: 14,
  },
  categoryCard: {
    backgroundColor: "#131b2e",
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  categoryInfo: {
    flex: 1,
  },
  categoryName: {
    fontSize: 15,
    fontWeight: "600",
    color: "#f1f5f9",
  },
  categoryAmount: {
    fontSize: 16,
    fontWeight: "700",
    color: "#e2e8f0",
  },
});
