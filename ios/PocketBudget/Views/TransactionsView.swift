import SwiftUI

struct TransactionsView: View {
    @EnvironmentObject private var store: BudgetStore

    var body: some View {
        NavigationStack {
            List {
                ForEach(store.transactions) { transaction in
                    TransactionRow(transaction: transaction)
                }
            }
            .listStyle(.plain)
            .navigationTitle("Spending")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await store.sync() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(store.isLoading)
                    .accessibilityLabel("Sync transactions")
                }
            }
        }
    }
}

struct TransactionRow: View {
    var transaction: LedgerTransaction

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(transaction.displayName)
                        .font(.subheadline.weight(.semibold))
                    if transaction.pending {
                        Text("Pending")
                            .font(.caption2.weight(.bold))
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Color.orange.opacity(0.18))
                            .clipShape(Capsule())
                    }
                }
                Text([transaction.accountName, transaction.categoryName, transaction.date].compactMap { $0 }.joined(separator: " · "))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            Spacer()

            Text(transaction.amountCents.moneyString)
                .font(.subheadline.monospacedDigit().weight(.semibold))
                .foregroundStyle(transaction.amountCents < 0 ? .green : .primary)
        }
        .padding(.vertical, 6)
    }
}

