import Foundation
import SwiftUI

struct AppConfiguration: Equatable {
    var backendURL: String
    var apiToken: String

    var isReady: Bool {
        URL(string: backendURL) != nil && !apiToken.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
}

struct DashboardSummary: Codable {
    var month: String
    var accounts: [AccountSnapshot]
    var budgets: [BudgetCategorySummary]
    var recentTransactions: [LedgerTransaction]
    var investments: InvestmentSummary?

    static let sample = DashboardSummary(
        month: "Setup",
        accounts: [
            AccountSnapshot(id: "sample-checking", name: "Checking", type: "depository", subtype: "checking", balanceCents: 184250),
            AccountSnapshot(id: "sample-card", name: "Credit Card", type: "credit", subtype: "credit card", balanceCents: -28410)
        ],
        budgets: [
            BudgetCategorySummary(id: "necessities", name: "Necessities", iconSystemName: "house.fill", colorHex: "#2563EB", monthlyLimitCents: 180000, spentCents: 94000),
            BudgetCategorySummary(id: "fun", name: "Fun", iconSystemName: "sparkles", colorHex: "#7C3AED", monthlyLimitCents: 40000, spentCents: 18250),
            BudgetCategorySummary(id: "girlfriend", name: "Girlfriend", iconSystemName: "heart.fill", colorHex: "#DB2777", monthlyLimitCents: 30000, spentCents: 8250)
        ],
        recentTransactions: [
            LedgerTransaction(id: "sample-1", date: "2026-08-14", name: "Grocery Store", merchantName: "Grocery Store", amountCents: 7421, accountName: "Checking", categoryId: "necessities", categoryName: "Necessities", pending: false),
            LedgerTransaction(id: "sample-2", date: "2026-08-13", name: "Dinner", merchantName: "Dinner", amountCents: 4650, accountName: "Credit Card", categoryId: "fun", categoryName: "Fun", pending: false)
        ],
        investments: InvestmentSummary(totalValueCents: 0, holdings: [])
    )
}

struct AccountSnapshot: Codable, Identifiable {
    var id: String
    var name: String
    var type: String
    var subtype: String?
    var balanceCents: Int
}

struct BudgetCategorySummary: Codable, Identifiable, Equatable {
    var id: String
    var name: String
    var iconSystemName: String
    var colorHex: String
    var monthlyLimitCents: Int
    var spentCents: Int

    var remainingCents: Int {
        monthlyLimitCents - spentCents
    }

    var progress: Double {
        guard monthlyLimitCents > 0 else { return 0 }
        return min(Double(spentCents) / Double(monthlyLimitCents), 1.5)
    }
}

struct LedgerTransaction: Codable, Identifiable, Equatable {
    var id: String
    var date: String
    var name: String
    var merchantName: String?
    var amountCents: Int
    var accountName: String?
    var categoryId: String?
    var categoryName: String?
    var pending: Bool

    var displayName: String {
        merchantName?.isEmpty == false ? merchantName! : name
    }
}

struct InvestmentSummary: Codable, Equatable {
    var totalValueCents: Int
    var holdings: [InvestmentHolding]
}

struct InvestmentHolding: Codable, Identifiable, Equatable {
    var id: String
    var name: String
    var tickerSymbol: String?
    var quantity: Double
    var valueCents: Int
}

struct LinkSessionResponse: Codable {
    var linkUrl: URL
    var expiresAt: String
}

struct EmptyResponse: Codable {}

extension Int {
    var moneyString: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.maximumFractionDigits = 2
        formatter.minimumFractionDigits = 2
        return formatter.string(from: NSNumber(value: Double(self) / 100.0)) ?? "$0.00"
    }
}

extension Color {
    init(hex: String) {
        let cleaned = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var value: UInt64 = 0
        Scanner(string: cleaned).scanHexInt64(&value)

        let red: UInt64
        let green: UInt64
        let blue: UInt64

        switch cleaned.count {
        case 6:
            red = (value >> 16) & 0xFF
            green = (value >> 8) & 0xFF
            blue = value & 0xFF
        default:
            red = 37
            green = 99
            blue = 235
        }

        self.init(
            .sRGB,
            red: Double(red) / 255.0,
            green: Double(green) / 255.0,
            blue: Double(blue) / 255.0,
            opacity: 1.0
        )
    }
}

