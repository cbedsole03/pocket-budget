import SwiftUI

@main
struct PocketBudgetApp: App {
    @StateObject private var store = BudgetStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
        }
    }
}

