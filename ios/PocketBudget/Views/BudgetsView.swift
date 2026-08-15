import SwiftUI

struct BudgetsView: View {
    @EnvironmentObject private var store: BudgetStore

    var body: some View {
        NavigationStack {
            List {
                ForEach(store.dashboard.budgets) { budget in
                    NavigationLink {
                        BudgetDetailView(budget: budget)
                    } label: {
                        BudgetProgressRow(budget: budget)
                    }
                    .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                    .listRowSeparator(.hidden)
                }
            }
            .listStyle(.plain)
            .navigationTitle("Budgets")
        }
    }
}

struct BudgetDetailView: View {
    @EnvironmentObject private var store: BudgetStore
    var budget: BudgetCategorySummary
    @State private var monthlyLimit: String

    init(budget: BudgetCategorySummary) {
        self.budget = budget
        _monthlyLimit = State(initialValue: String(format: "%.2f", Double(budget.monthlyLimitCents) / 100.0))
    }

    var body: some View {
        Form {
            Section("Current Month") {
                BudgetProgressRow(budget: budget)
            }

            Section("Limit") {
                TextField("Monthly limit", text: $monthlyLimit)
                    .keyboardType(.decimalPad)

                Button("Save Limit") {
                    Task {
                        let cents = Int(((Double(monthlyLimit) ?? 0) * 100.0).rounded())
                        await store.updateBudget(budget, monthlyLimitCents: max(cents, 0))
                    }
                }
                .disabled(store.isLoading)
            }
        }
        .navigationTitle(budget.name)
    }
}

