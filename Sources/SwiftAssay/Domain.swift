public struct DraftLine: Sendable, Equatable {
    public let sku: String
    public let quantity: Int
    public let unitPriceCents: Int

    public init(sku: String, quantity: Int, unitPriceCents: Int) {
        self.sku = sku
        self.quantity = quantity
        self.unitPriceCents = unitPriceCents
    }
}

public struct Order: Sendable, Equatable {
    public let identifier: String
    public let lines: [DraftLine]
}

public enum OrderDecision: Sendable, Equatable {
    case accepted(Order)
    case rejected(String)
}

public func createOrder(identifier: String, lines: [DraftLine]) -> OrderDecision {
    guard containsNonWhitespace(identifier) else {
        return .rejected("order identifier is required")
    }
    guard !lines.isEmpty else {
        return .rejected("an order needs at least one line")
    }
    guard lines.allSatisfy({ containsNonWhitespace($0.sku) }) else {
        return .rejected("each line needs a SKU")
    }
    guard lines.allSatisfy({ $0.quantity > 0 }) else {
        return .rejected("quantity must be positive")
    }
    guard lines.allSatisfy({ $0.unitPriceCents >= 0 }) else {
        return .rejected("unit price cannot be negative")
    }
    return .accepted(Order(identifier: identifier, lines: lines))
}

public func totalCents(order: Order) -> Int {
    order.lines.reduce(0) { total, line in
        total + line.quantity * line.unitPriceCents
    }
}

private func containsNonWhitespace(_ value: String) -> Bool {
    value.contains { !$0.isWhitespace }
}
