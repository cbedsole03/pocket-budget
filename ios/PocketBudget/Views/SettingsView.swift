import SwiftUI

struct SettingsView: View {
    @EnvironmentObject private var store: BudgetStore

    var body: some View {
        NavigationStack {
            Form {
                Section("Backend") {
                    TextField("Backend URL", text: $store.backendURL)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()

                    SecureField("API token", text: $store.apiToken)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()

                    Button("Save Settings") {
                        store.saveSettings()
                    }
                }

                Section("Bank Connection") {
                    Button {
                        Task { await store.connectBank() }
                    } label: {
                        Label("Connect Bank Account", systemImage: "link.circle")
                    }
                    .disabled(store.isLoading || !store.isConfigured)

                    Button {
                        Task { await store.sync() }
                    } label: {
                        Label("Sync Now", systemImage: "arrow.clockwise")
                    }
                    .disabled(store.isLoading || !store.isConfigured)
                }

                Section("Status") {
                    Text(store.statusMessage ?? "Ready")
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Settings")
        }
    }
}

