import Foundation

@MainActor
final class BudgetStore: ObservableObject {
    @Published var dashboard: DashboardSummary = .sample
    @Published var transactions: [LedgerTransaction] = DashboardSummary.sample.recentTransactions
    @Published var backendURL: String
    @Published var apiToken: String
    @Published var statusMessage: String?
    @Published var isLoading = false

    private let apiClient = APIClient()
    private let bankLinker = BankLinker()
    private let tokenService = "PocketBudget"
    private let tokenAccount = "BackendAPIToken"

    var config: AppConfiguration {
        AppConfiguration(backendURL: backendURL, apiToken: apiToken)
    }

    var isConfigured: Bool {
        config.isReady
    }

    init() {
        backendURL = UserDefaults.standard.string(forKey: "backendURL") ?? "http://127.0.0.1:8000"
        apiToken = (try? KeychainStore.load(service: tokenService, account: tokenAccount)) ?? ""
    }

    func saveSettings() {
        UserDefaults.standard.set(backendURL, forKey: "backendURL")
        do {
            try KeychainStore.save(apiToken, service: tokenService, account: tokenAccount)
            statusMessage = "Settings saved."
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func refresh() async {
        guard isConfigured else {
            dashboard = .sample
            transactions = DashboardSummary.sample.recentTransactions
            statusMessage = "Add your backend URL and API token in Settings."
            return
        }

        await load("Refreshing") {
            dashboard = try await apiClient.dashboard(config: config)
            transactions = try await apiClient.transactions(config: config)
            statusMessage = "Updated."
        }
    }

    func sync() async {
        guard isConfigured else {
            statusMessage = "Settings are not configured."
            return
        }

        await load("Syncing") {
            try await apiClient.sync(config: config)
            dashboard = try await apiClient.dashboard(config: config)
            transactions = try await apiClient.transactions(config: config)
            statusMessage = "Bank sync complete."
        }
    }

    func connectBank() async {
        guard isConfigured else {
            statusMessage = "Settings are not configured."
            return
        }

        await load("Opening Plaid") {
            let response = try await apiClient.createLinkSession(config: config)
            try await bankLinker.start(url: response.linkUrl)
            try await apiClient.sync(config: config)
            dashboard = try await apiClient.dashboard(config: config)
            transactions = try await apiClient.transactions(config: config)
            statusMessage = "Bank connected."
        }
    }

    func updateBudget(_ budget: BudgetCategorySummary, monthlyLimitCents: Int) async {
        guard isConfigured else {
            statusMessage = "Settings are not configured."
            return
        }

        await load("Saving budget") {
            _ = try await apiClient.updateBudget(id: budget.id, monthlyLimitCents: monthlyLimitCents, config: config)
            dashboard = try await apiClient.dashboard(config: config)
            statusMessage = "Budget saved."
        }
    }

    private func load(_ label: String, operation: () async throws -> Void) async {
        isLoading = true
        statusMessage = "\(label)..."
        defer { isLoading = false }

        do {
            try await operation()
        } catch {
            statusMessage = error.localizedDescription
        }
    }
}

