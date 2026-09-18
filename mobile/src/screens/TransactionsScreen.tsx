import React, { useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Modal,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import {
  Transaction,
  useAccounts,
  useCreateTransaction,
  useTransactions,
} from "../api/hooks";

export default function TransactionsScreen() {
  const { data: transactions, isLoading, refetch, isRefetching } = useTransactions();
  const { data: accounts } = useAccounts();
  const createMutation = useCreateTransaction();

  const [modalVisible, setModalVisible] = useState(false);
  const [merchant, setMerchant] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!merchant.trim() || !amount.trim()) {
      setFormError("Merchant and amount are required.");
      return;
    }

    const defaultAccount = accounts?.[0]?.id || 1;
    setFormError(null);
    try {
      await createMutation.mutateAsync({
        merchant: merchant.trim(),
        amount: amount.trim(),
        date: new Date().toISOString().split("T")[0],
        description: description.trim(),
        account: defaultAccount,
      });
      setMerchant("");
      setAmount("");
      setDescription("");
      setModalVisible(false);
    } catch (err: any) {
      setFormError(err.message || "Failed to create transaction");
    }
  };

  const renderItem = ({ item }: { item: Transaction }) => {
    const formattedAmount = Number(item.amount).toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

    return (
      <View style={styles.txnCard}>
        <View style={styles.txnLeft}>
          <Text style={styles.merchant}>{item.merchant}</Text>
          <Text style={styles.meta}>
            {item.category_name || "Auto-categorizing..."} • {item.date}
          </Text>
        </View>
        <Text style={styles.amount}>₹{formattedAmount}</Text>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>Transactions</Text>
          <Text style={styles.subtitle}>Recent spending activity</Text>
        </View>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => setModalVisible(true)}
        >
          <Text style={styles.addButtonText}>+ Add</Text>
        </TouchableOpacity>
      </View>

      {isLoading && !transactions ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#10b981" />
        </View>
      ) : (
        <FlatList
          data={transactions || []}
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
              <Text style={styles.emptyText}>No transactions found.</Text>
            </View>
          }
        />
      )}

      {/* Add Transaction Modal */}
      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Add Transaction</Text>

            {formError && (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>{formError}</Text>
              </View>
            )}

            <Text style={styles.label}>Merchant / Payee</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g. Swiggy, Uber, Amazon"
              placeholderTextColor="#64748b"
              value={merchant}
              onChangeText={setMerchant}
            />

            <Text style={styles.label}>Amount (₹)</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g. 450.00"
              placeholderTextColor="#64748b"
              value={amount}
              onChangeText={setAmount}
              keyboardType="decimal-pad"
            />

            <Text style={styles.label}>Description (Optional)</Text>
            <TextInput
              style={styles.input}
              placeholder="e.g. Team lunch"
              placeholderTextColor="#64748b"
              value={description}
              onChangeText={setDescription}
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setModalVisible(false)}
              >
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.saveBtn, createMutation.isPending && styles.disabledBtn]}
                onPress={handleCreate}
                disabled={createMutation.isPending}
              >
                <Text style={styles.saveBtnText}>
                  {createMutation.isPending ? "Saving..." : "Save"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
  addButton: {
    backgroundColor: "#10b981",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 10,
  },
  addButtonText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 14,
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
  txnCard: {
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
  txnLeft: {
    flex: 1,
    paddingRight: 10,
  },
  merchant: {
    fontSize: 15,
    fontWeight: "700",
    color: "#f1f5f9",
  },
  meta: {
    fontSize: 12,
    color: "#64748b",
    marginTop: 4,
  },
  amount: {
    fontSize: 16,
    fontWeight: "700",
    color: "#e2e8f0",
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
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.7)",
    justifyContent: "flex-end",
  },
  modalCard: {
    backgroundColor: "#131b2e",
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: "800",
    color: "#f8fafc",
    marginBottom: 16,
  },
  errorBox: {
    backgroundColor: "rgba(239, 68, 68, 0.15)",
    borderColor: "#ef4444",
    borderWidth: 1,
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
  },
  errorText: {
    color: "#f87171",
    fontSize: 12,
    textAlign: "center",
  },
  label: {
    fontSize: 13,
    color: "#cbd5e1",
    fontWeight: "600",
    marginBottom: 6,
    marginTop: 10,
  },
  input: {
    backgroundColor: "#0b1120",
    borderWidth: 1,
    borderColor: "#334155",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#ffffff",
    fontSize: 15,
  },
  modalActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 12,
    marginTop: 24,
  },
  cancelBtn: {
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderRadius: 10,
  },
  cancelBtnText: {
    color: "#94a3b8",
    fontWeight: "600",
  },
  saveBtn: {
    backgroundColor: "#10b981",
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 10,
  },
  disabledBtn: {
    opacity: 0.6,
  },
  saveBtnText: {
    color: "#ffffff",
    fontWeight: "700",
  },
});
