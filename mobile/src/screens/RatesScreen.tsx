import React from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useMetalRates } from "../api/hooks";

export default function RatesScreen() {
  const { data: rates, isLoading, refetch, isRefetching } = useMetalRates();

  if (isLoading && !rates) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#eab308" />
      </View>
    );
  }

  const renderRateRow = (label: string, price: number) => {
    const formatted = price.toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    return (
      <View key={label} style={styles.rateRow}>
        <Text style={styles.purityLabel}>{label}</Text>
        <Text style={styles.rateValue}>₹{formatted}/g</Text>
      </View>
    );
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={isRefetching}
          onRefresh={refetch}
          tintColor="#eab308"
        />
      }
    >
      <View style={styles.header}>
        <Text style={styles.title}>Live Precious Metals</Text>
        <Text style={styles.subtitle}>
          Spot bullion rates in INR (Auto-refreshed every 5 min)
        </Text>
        {rates?.last_updated && (
          <Text style={styles.timestamp}>
            Updated: {new Date(rates.last_updated).toLocaleTimeString("en-IN")}
          </Text>
        )}
      </View>

      {/* Gold Card */}
      <View style={[styles.metalCard, styles.goldCard]}>
        <View style={styles.cardHeader}>
          <Text style={styles.metalIcon}>🥇</Text>
          <Text style={styles.metalTitle}>Gold</Text>
        </View>
        <View style={styles.ratesTable}>
          {rates?.gold && Object.keys(rates.gold).length > 0 ? (
            Object.entries(rates.gold).map(([purity, val]) =>
              renderRateRow(purity, val)
            )
          ) : (
            <Text style={styles.noData}>No gold rate snapshot available.</Text>
          )}
        </View>
      </View>

      {/* Silver Card */}
      <View style={[styles.metalCard, styles.silverCard]}>
        <View style={styles.cardHeader}>
          <Text style={styles.metalIcon}>🥈</Text>
          <Text style={styles.metalTitle}>Silver</Text>
        </View>
        <View style={styles.ratesTable}>
          {rates?.silver && Object.keys(rates.silver).length > 0 ? (
            Object.entries(rates.silver).map(([purity, val]) =>
              renderRateRow(purity, val)
            )
          ) : (
            <Text style={styles.noData}>No silver rate snapshot available.</Text>
          )}
        </View>
      </View>

      {/* Platinum Card */}
      <View style={[styles.metalCard, styles.platCard]}>
        <View style={styles.cardHeader}>
          <Text style={styles.metalIcon}>⚪</Text>
          <Text style={styles.metalTitle}>Platinum</Text>
        </View>
        <View style={styles.ratesTable}>
          {rates?.platinum && Object.keys(rates.platinum).length > 0 ? (
            Object.entries(rates.platinum).map(([purity, val]) =>
              renderRateRow(purity, val)
            )
          ) : (
            <Text style={styles.noData}>No platinum rate snapshot available.</Text>
          )}
        </View>
      </View>
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
  title: {
    fontSize: 24,
    fontWeight: "800",
    color: "#f8fafc",
  },
  subtitle: {
    fontSize: 13,
    color: "#94a3b8",
    marginTop: 4,
  },
  timestamp: {
    fontSize: 12,
    color: "#64748b",
    marginTop: 6,
  },
  metalCard: {
    backgroundColor: "#131b2e",
    borderRadius: 18,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
  },
  goldCard: {
    borderColor: "rgba(234, 179, 8, 0.3)",
  },
  silverCard: {
    borderColor: "rgba(148, 163, 184, 0.3)",
  },
  platCard: {
    borderColor: "rgba(56, 189, 248, 0.3)",
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 14,
  },
  metalIcon: {
    fontSize: 20,
    marginRight: 8,
  },
  metalTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#f8fafc",
  },
  ratesTable: {
    gap: 8,
  },
  rateRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 4,
    borderBottomWidth: 1,
    borderBottomColor: "#1e293b",
  },
  purityLabel: {
    fontSize: 14,
    color: "#94a3b8",
    fontWeight: "500",
  },
  rateValue: {
    fontSize: 15,
    fontWeight: "700",
    color: "#f1f5f9",
  },
  noData: {
    color: "#64748b",
    fontSize: 13,
    fontStyle: "italic",
  },
});
