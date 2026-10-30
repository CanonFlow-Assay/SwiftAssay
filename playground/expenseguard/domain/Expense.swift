enum Decision: Equatable {
    case approved(Int)
    case needsReview(Int)
    case invalid(String)
}

func decide(amount: Int, currency: String, memo: String, limit: Int) -> Decision {
    if limit <= 0 { return .invalid("policy") }
    if amount <= 0 { return .invalid("amount") }
    if currency != "USD" { return .invalid("currency") }
    if memo.allSatisfy({ $0.isWhitespace }) { return .invalid("memo") }
    if memo.unicodeScalars.count > 200 { return .invalid("memo-too-long") }
    if amount > limit { return .needsReview(amount) }
    return .approved(amount)
}
