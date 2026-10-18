import Testing
@testable import SwiftAssay

@Test func pureTaggedOutcomeIsClean() {
    let findings = inspect(path: "domain/order.swift", source: "func decide() -> Decision { .accepted(1) }")
    #expect(findings.isEmpty)
}

@Test func selectedHazardsHaveStableLocations() {
    let source = "try! decode()\nprint(\"effect\")\nlet value: String! = nil"
    let findings = inspect(path: "domain/order.swift", source: source)
    #expect(findings.map(\.ruleId) == ["SWA-F001", "SWA-F002", "SWA-F003"])
    #expect(findings.map(\.line) == [1, 2, 3])
}

@Test func receiptIsDeterministic() throws {
    let findings = inspect(path: "domain/order.swift", source: "print(\"effect\")")
    #expect(try renderReceipt(root: "examples/clean", scannedFiles: 1, findings: findings) == renderReceipt(root: "examples/clean", scannedFiles: 1, findings: findings))
}

@Test func validOrderHasDeterministicTotal() {
    let decision = createOrder(identifier: "order-42", lines: [DraftLine(sku: "book", quantity: 2, unitPriceCents: 1_250)])
    guard case let .accepted(order) = decision else {
        Issue.record("valid input should be accepted")
        return
    }
    #expect(totalCents(order: order) == 2_500)
}

@Test func invalidOrderIsAValue() {
    #expect(createOrder(identifier: "", lines: []) == .rejected("order identifier is required"))
}
