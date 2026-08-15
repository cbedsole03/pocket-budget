import SwiftUI

struct RootView: View {
    @EnvironmentObject private var store: BudgetStore

    var body: some View {
        TabView {
            DashboardView()
                .tabItem {
                    Label("Dashboard", systemImage: "chart.pie.fill")
                }

            TransactionsView()
                .tabItem {
                    Label("Spending", systemImage: "list.bullet.rectangle")
                }

            BudgetsView()
                .tabItem {
                    Label("Budgets", systemImage: "target")
                }

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gearshape.fill")
                }
        }
        .task {
            await store.refresh()
        }
    }
}

