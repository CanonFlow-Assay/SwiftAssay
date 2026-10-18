import Foundation

/// A selected lexical rule. It is not a parser or a semantic proof.
public struct Rule: Sendable, Equatable {
    public let id: String
    public let message: String
    public let forbiddenFragments: [String]

    public init(id: String, message: String, forbiddenFragments: [String]) {
        self.id = id
        self.message = message
        self.forbiddenFragments = forbiddenFragments
    }
}

public struct Finding: Sendable, Equatable, Comparable, Encodable {
    public let path: String
    public let line: Int
    public let column: Int
    public let ruleId: String
    public let message: String

    public static func < (left: Finding, right: Finding) -> Bool {
        (left.path, left.line, left.column, left.ruleId) < (right.path, right.line, right.column, right.ruleId)
    }
}

public let rules: [Rule] = [
    Rule(
        id: "SWA-F001",
        message: "Expected domain failures are values, not forced failures or traps.",
        forbiddenFragments: ["try!", "fatalError(", "preconditionFailure("]
    ),
    Rule(
        id: "SWA-F002",
        message: "Domain code does not import or perform named effects.",
        forbiddenFragments: ["import Foundation", "FileManager", "URLSession", "print("]
    ),
    Rule(
        id: "SWA-F003",
        message: "Domain code does not use implicitly unwrapped optional values.",
        forbiddenFragments: ["! =", "!)", "!."]
    ),
]

/// Inspects one source string without reading a file or mutating shared state.
public func inspect(path: String, source: String) -> [Finding] {
    var findings: [Finding] = []
    for (lineOffset, line) in source.split(separator: "\n", omittingEmptySubsequences: false).enumerated() {
        let text = String(line)
        for rule in rules {
            guard let fragment = rule.forbiddenFragments.first(where: { text.contains($0) }),
                  let range = text.range(of: fragment)
            else {
                continue
            }
            findings.append(
                Finding(
                    path: path,
                    line: lineOffset + 1,
                    column: text.distance(from: text.startIndex, to: range.lowerBound) + 1,
                    ruleId: rule.id,
                    message: rule.message
                )
            )
        }
    }
    return findings.sorted()
}

private struct Receipt: Encodable {
    let findings: [Finding]
    let root: String
    let scannedFiles: Int
    let schemaVersion: String
    let verdict: String
}

public func renderReceipt(root: String, scannedFiles: Int, findings: [Finding]) throws -> String {
    let receipt = Receipt(
        findings: findings,
        root: root,
        scannedFiles: scannedFiles,
        schemaVersion: "swift-assay/v0.1",
        verdict: findings.isEmpty ? "Pass" : "Fail"
    )
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
    return String(decoding: try encoder.encode(receipt), as: UTF8.self)
}
