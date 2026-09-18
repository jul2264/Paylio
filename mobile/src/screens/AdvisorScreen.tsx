import React from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { Insight, useAdvisorFeed, useRefreshAdvisor } from "../api/hooks";

export default function AdvisorScreen() {
  const { data: insights, isLoading, refetch, isRefetching } = useAdvisorFeed();
  const refreshMutation = useRefreshAdvisor();

  const handleManualRefresh = async () => {
    await refreshMutation.mutateAsync();
  };

  const getSeverityBadgeStyle = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return { bg: "rgba(239, 68, 68, 0.15)", text: "#f87171", border: "#ef4444" };
      case "WARNING":
        return { bg: "rgba(245, 158, 11, 0.15)", text: "#fbbf24", border: "#f59e0b" };
      default:
        return { bg: "rgba(56, 189, 248, 0.15)", text: "#38bdf8", border: "#0284c7" };
    }
  };

  const renderItem = ({ item }: { item: Insight }) => {
    const badge = getSeverityBadgeStyle(item.severity);
    const advice = item.advice?.[0];

    return (
      <View style={styles.insightCard}>
        <View style={styles.insightHeader}>
          <View
            style={[
              styles.badge,
              { backgroundColor: badge.bg, borderColor: badge.border },
            ]}
          >
            <Text style={[styles.badgeText, { color: badge.text }]}>
              {item.severity}
            </Text>
          </View>
          <Text style={styles.dateText}>{item.period_end}</Text>
        </View>

        <Text style={styles.summary}>{item.summary}</Text>

        {advice && (
          <View style={styles.adviceBox}>
            <Text style={styles.adviceLabel}>💡 Robo-Advisor Recommendation</Text>
            <Text style={styles.adviceBody}>{advice.body}</Text>
          </View>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Advisor Feed</Text>
          <Text style={styles.subtitle}>Automated financial intelligence</Text>
        </View>
        <TouchableOpacity
          style={[styles.refreshBtn, refreshMutation.isPending && styles.disabledBtn]}
          onPress={handleManualRefresh}
          disabled={refreshMutation.isPending}
        >
          {refreshMutation.isPending ? (
            <ActivityIndicator size="small" color="#ffffff" />
          ) : (
            <Text style={styles.refreshBtnText}>⚡ Analyze</Text>
          )}
        </TouchableOpacity>
      </View>

      {isLoading && !insights ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#10b981" />
        </View>
      ) : (
        <FlatList
          data={insights || []}
          keyExtractor={(item) => item.id.toString()}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={refetch}
              tintColor="#10b981"
            />
          }
          ListEmptyComponent={
            <View style={styles.emptyCard}>
              <Text style={styles.emptyText}>
                No insights yet. Tap 'Analyze' to run the robo-advisor rule engine.
              </Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#090d16",
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 14,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  title: {
    fontSize: 24,
    fontWeight: "800",
    color: "#f8fafc",
  },
  subtitle: {
    fontSize: 13,
    color: "#94a3b8",
    marginTop: 2,
  },
  refreshBtn: {
    backgroundColor: "#6366f1",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 10,
  },
  disabledBtn: {
    opacity: 0.6,
  },
  refreshBtnText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 13,
  },
  list: {
    padding: 20,
    paddingTop: 6,
  },
  centerContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  insightCard: {
    backgroundColor: "#131b2e",
    borderRadius: 16,
    padding: 18,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  insightHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: "800",
  },
  dateText: {
    fontSize: 12,
    color: "#64748b",
  },
  summary: {
    fontSize: 15,
    fontWeight: "600",
    color: "#f1f5f9",
    lineHeight: 22,
    marginBottom: 12,
  },
  adviceBox: {
    backgroundColor: "#0b1120",
    borderRadius: 10,
    padding: 12,
    borderLeftWidth: 3,
    borderLeftColor: "#6366f1",
  },
  adviceLabel: {
    fontSize: 12,
    fontWeight: "700",
    color: "#818cf8",
    marginBottom: 4,
  },
  adviceBody: {
    fontSize: 13,
    color: "#cbd5e1",
    lineHeight: 18,
  },
  emptyCard: {
    backgroundColor: "#131b2e",
    padding: 24,
    borderRadius: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  emptyText: {
    color: "#64748b",
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
  },
});
