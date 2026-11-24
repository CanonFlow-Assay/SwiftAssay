import Foundation

let cases: [(String, [String: String], String)] = [
    (
        "valid",
        ["Service:Endpoint": "https://api.example.test", "Service:RetryLimit": "3", "Service:Mode": "read-only"],
        "loaded|https://api.example.test/|3|ReadOnly"
    ),
    (
        "missing",
        ["Service:Endpoint": "https://api.example.test", "Service:RetryLimit": "3"],
        "rejected|missing:Service:Mode"
    ),
    (
        "bad-uri",
        ["Service:Endpoint": "not-a-uri", "Service:RetryLimit": "3", "Service:Mode": "write"],
        "rejected|invalid-uri:Service:Endpoint"
    ),
    (
        "bad-limit",
        ["Service:Endpoint": "https://api.example.test", "Service:RetryLimit": "0", "Service:Mode": "write"],
        "rejected|invalid-range:Service:RetryLimit"
    ),
    (
        "bad-mode",
        ["Service:Endpoint": "https://api.example.test", "Service:RetryLimit": "3", "Service:Mode": "admin"],
        "rejected|invalid-mode:Service:Mode"
    ),
    (
        "multiple-issues",
        ["Service:Endpoint": "ftp://bad.example.test", "Service:RetryLimit": "99"],
        "rejected|invalid-uri:Service:Endpoint;invalid-range:Service:RetryLimit;missing:Service:Mode"
    )
]

for (name, values, expected) in cases {
    let actual = canonicalConfiguration(loadConfiguration(values))
    if actual != expected {
        FileHandle.standardError.write(Data("\(name): expected \(expected), got \(actual)\n".utf8))
        exit(1)
    }
}
print("Swift configuration firewall: \(cases.count) cases passed.")
