import SwiftUI

struct DashboardView: View {
    @EnvironmentObject private var store: BudgetStore

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    StatusBanner()

                    AccountStrip(accounts: store.dashboard.accounts)

                    VStack(alignment: .leading, spacing: 12) {
                        SectionHeader(title: "Budgets", actionTitle: "Sync") {
                            Task { await store.sync() }
                        }

                        ForEach(store.dashboard.budgets) { budget in
                            BudgetProgressRow(budget: budget)
                        }
                    }

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Recent Spending")
                            .font(.headline)
                        ForEach(store.dashboard.recentTransactions.prefix(5)) { transaction in
                            TransactionRow(transaction: transaction)
                        }
                    }
                }
                .padding()
            }
            .navigationTitle("PocketBudget")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await store.connectBank() }
                    } label: {
                        Image(systemName: "link.circle.fill")
                    }
                    .disabled(store.isLoading)
                    .accessibilityLabel("Connect bank")
                }
            }
        }
    }
}

private struct StatusBanner: View {
    @EnvironmentObject private var store: BudgetStore

    var body: some View {
        if let message = store.statusMessage {
            HStack(spacing: 10) {
                if store.isLoading {
                    ProgressView()
                } else {
                    Image(systemName: store.isConfigured ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                }
                Text(message)
                    .font(.subheadline)
                    .lineLimit(3)
                Spacer()
            }
            .padding(12)
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        }
    }
}

private struct AccountStrip: View {
    var accounts: [AccountSnapshot]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Accounts")
                .font(.headline)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(accounts) { account in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(account.name)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                            Text(account.balanceCents.moneyString)
                                .font(.title3.weight(.semibold))
                            Text(account.subtype ?? account.type)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .frame(width: 170, alignment: .leading)
                        .padding(14)
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
                    }
                }
            }
        }
    }
}

struct BudgetProgressRow: View {
    var budget: BudgetCategorySummary

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 10) {
                Image(systemName: budget.iconSystemName)
                    .foregroundStyle(Color(hex: budget.colorHex))
                    .frame(width: 24)
                Text(budget.name)
                    .font(.subheadline.weight(.semibold))
                Spacer()
                Text("\(budget.spentCents.moneyString) / \(budget.monthlyLimitCents.moneyString)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            ProgressView(value: min(budget.progress, 1.0))
                .tint(Color(hex: budget.colorHex))

            HStack {
                Text("\(budget.remainingCents.moneyString) left")
                Spacer()
                Text("\(Int(budget.progress * 100))%")
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .padding(14)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
    }
}

struct SectionHeader: View {
    var title: String
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        HStack {
            Text(title)
                .font(.headline)
            Spacer()
            if let actionTitle, let action {
                Button(actionTitle, action: action)
                    .font(.subheadline.weight(.semibold))
            }
        }
    }
}

