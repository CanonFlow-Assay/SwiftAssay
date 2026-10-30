import Foundation

struct Case {
    let id: String
    let amount: Int
    let currency: String
    let memo: String
    let limit: Int
    let expected: Decision
}

let mode = CommandLine.arguments.count == 2 ? CommandLine.arguments[1] : ""
guard mode == "baseline" || mode == "expanded" else { exit(64) }
let cases: [Case] = [
    Case(id: "approved", amount: 2500, currency: "USD", memo: "lunch", limit: 10000, expected: .approved(2500)),
    Case(id: "negative", amount: -1, currency: "USD", memo: "lunch", limit: 10000, expected: .invalid("amount")),
    Case(id: "over-limit", amount: 10001, currency: "USD", memo: "lunch", limit: 10000, expected: .needsReview(10001)),
    Case(id: "currency", amount: 2500, currency: "EUR", memo: "lunch", limit: 10000, expected: .invalid("currency")),
    Case(id: "empty-memo", amount: 2500, currency: "USD", memo: "", limit: 10000, expected: .invalid("memo")),
    Case(id: "zero-policy", amount: 2500, currency: "USD", memo: "lunch", limit: 0, expected: .invalid("policy")),
    Case(id: "zero-amount", amount: 0, currency: "USD", memo: "lunch", limit: 10000, expected: .invalid("amount")),
    Case(id: "exact-limit", amount: 10000, currency: "USD", memo: "lunch", limit: 10000, expected: .approved(10000)),
    Case(id: "smallest-amount", amount: 1, currency: "USD", memo: "lunch", limit: 10000, expected: .approved(1)),
    Case(id: "blank-memo", amount: 2500, currency: "USD", memo: " \t", limit: 10000, expected: .invalid("memo")),
    Case(id: "negative-policy", amount: 2500, currency: "USD", memo: "lunch", limit: -1, expected: .invalid("policy")),
    Case(id: "large-amount", amount: 2147483647, currency: "USD", memo: "lunch", limit: 10000, expected: .needsReview(2147483647)),
]
let selected = mode == "baseline" ? Array(cases.prefix(6)) : cases
let failures = selected.reduce(0) { count, test in
    let passed = decide(amount: test.amount, currency: test.currency, memo: test.memo, limit: test.limit) == test.expected
    print("CASE\t\(test.id)\t\(passed ? "PASS" : "FAIL")")
    return count + (passed ? 0 : 1)
}
exit(failures == 0 ? 0 : 1)
