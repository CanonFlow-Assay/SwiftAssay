enum Decision: Equatable {
    case accepted(quantity: Int)
    case rejected(reason: String)
}

func decide(quantity: Int) -> Decision {
    quantity > 0 ? .accepted(quantity: quantity) : .rejected(reason: "quantity must be positive")
}
