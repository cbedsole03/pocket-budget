import Foundation

enum APIError: LocalizedError {
    case message(String)

    var errorDescription: String? {
        switch self {
        case .message(let value):
            return value
        }
    }
}

final class APIClient {
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init() {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        self.decoder = decoder

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        self.encoder = encoder
    }

    func dashboard(config: AppConfiguration) async throws -> DashboardSummary {
        try await request(path: "/api/summary", config: config)
    }

    func transactions(config: AppConfiguration) async throws -> [LedgerTransaction] {
        try await request(path: "/api/transactions", config: config)
    }

    func sync(config: AppConfiguration) async throws {
        let _: EmptyResponse = try await request(path: "/api/sync", method: "POST", config: config)
    }

    func updateBudget(id: String, monthlyLimitCents: Int, config: AppConfiguration) async throws -> BudgetCategorySummary {
        let body = BudgetUpdateRequest(monthlyLimitCents: monthlyLimitCents)
        return try await request(path: "/api/budgets/\(id)", method: "PUT", body: body, config: config)
    }

    func createLinkSession(config: AppConfiguration) async throws -> LinkSessionResponse {
        let body = LinkSessionRequest(returnUrl: "pocketbudget://plaid/connected")
        return try await request(path: "/api/link/session", method: "POST", body: body, config: config)
    }

    private func request<Response: Decodable>(
        path: String,
        method: String = "GET",
        config: AppConfiguration
    ) async throws -> Response {
        let emptyBody: EmptyBody? = nil
        return try await request(path: path, method: method, body: emptyBody, config: config)
    }

    private func request<Body: Encodable, Response: Decodable>(
        path: String,
        method: String = "GET",
        body: Body?,
        config: AppConfiguration
    ) async throws -> Response {
        guard let baseURL = URL(string: config.backendURL) else {
            throw APIError.message("Backend URL is not valid.")
        }

        let url = baseURL.appendingPathComponent(path.trimmingCharacters(in: CharacterSet(charactersIn: "/")))
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("Bearer \(config.apiToken)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let body {
            request.httpBody = try encoder.encode(body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.message("Backend did not return an HTTP response.")
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? "HTTP \(httpResponse.statusCode)"
            throw APIError.message(message)
        }

        if Response.self == EmptyResponse.self {
            return EmptyResponse() as! Response
        }
        return try decoder.decode(Response.self, from: data)
    }
}

private struct EmptyBody: Encodable {}

private struct BudgetUpdateRequest: Encodable {
    var monthlyLimitCents: Int
}

private struct LinkSessionRequest: Encodable {
    var returnUrl: String
}

