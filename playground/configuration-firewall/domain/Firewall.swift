enum ServiceMode: Equatable {
    case readOnly
    case write

    var label: String {
        switch self {
        case .readOnly: return "ReadOnly"
        case .write: return "Write"
        }
    }
}

struct ServiceConfiguration: Equatable {
    let endpoint: String
    let retryLimit: Int
    let mode: ServiceMode
}

struct ConfigurationIssue: Equatable {
    let code: String
    let key: String
}

enum ConfigurationLoad: Equatable {
    case loaded(ServiceConfiguration)
    case rejected([ConfigurationIssue])
}

func trimWhitespace(_ text: String) -> String {
    let scalars = Array(text.unicodeScalars)
    let start = scalars.firstIndex(where: { !CharacterSet_isSpace($0) }) ?? scalars.endIndex
    if start == scalars.endIndex { return "" }
    let end = scalars.lastIndex(where: { !CharacterSet_isSpace($0) }) ?? start
    var out = String.UnicodeScalarView()
    out.append(contentsOf: scalars[start...end])
    return String(out)
}

func CharacterSet_isSpace(_ scalar: UnicodeScalar) -> Bool {
    return scalar == " " || scalar == "\t" || scalar == "\n" || scalar == "\r"
}

func parseEndpoint(_ raw: String?) -> (String, [ConfigurationIssue]) {
    guard let text = raw else {
        return ("", [ConfigurationIssue(code: "missing", key: "Service:Endpoint")])
    }
    let trimmed = trimWhitespace(text)
    let isHttps = trimmed.hasPrefix("https://")
    let isHttp = trimmed.hasPrefix("http://")
    if !isHttps && !isHttp {
        return ("", [ConfigurationIssue(code: "invalid-uri", key: "Service:Endpoint")])
    }
    let prefixCount = isHttps ? 8 : 7
    let authority = String(trimmed.dropFirst(prefixCount))
    if authority.isEmpty || authority.hasPrefix("/") {
        return ("", [ConfigurationIssue(code: "invalid-uri", key: "Service:Endpoint")])
    }
    let normalized = authority.contains("/") ? trimmed : trimmed + "/"
    return (normalized, [])
}

func parseRetryLimit(_ raw: String?) -> (Int, [ConfigurationIssue]) {
    guard let text = raw else {
        return (0, [ConfigurationIssue(code: "missing", key: "Service:RetryLimit")])
    }
    let trimmed = trimWhitespace(text)
    guard let value = Int(trimmed), (1...10).contains(value) else {
        return (0, [ConfigurationIssue(code: "invalid-range", key: "Service:RetryLimit")])
    }
    return (value, [])
}

func parseMode(_ raw: String?) -> (ServiceMode, [ConfigurationIssue]) {
    guard let text = raw else {
        return (.readOnly, [ConfigurationIssue(code: "missing", key: "Service:Mode")])
    }
    switch text {
    case "read-only":
        return (.readOnly, [])
    case "write":
        return (.write, [])
    default:
        return (.readOnly, [ConfigurationIssue(code: "invalid-mode", key: "Service:Mode")])
    }
}

func loadConfiguration(_ values: [String: String]) -> ConfigurationLoad {
    let (endpoint, endpointIssues) = parseEndpoint(values["Service:Endpoint"])
    let (retryLimit, limitIssues) = parseRetryLimit(values["Service:RetryLimit"])
    let (mode, modeIssues) = parseMode(values["Service:Mode"])
    let issues = endpointIssues + limitIssues + modeIssues
    if issues.isEmpty {
        return .loaded(ServiceConfiguration(endpoint: endpoint, retryLimit: retryLimit, mode: mode))
    }
    return .rejected(issues)
}

func canonicalConfiguration(_ result: ConfigurationLoad) -> String {
    switch result {
    case .loaded(let cfg):
        return "loaded|\(cfg.endpoint)|\(cfg.retryLimit)|\(cfg.mode.label)"
    case .rejected(let issues):
        let joined = issues.map { "\($0.code):\($0.key)" }.joined(separator: ";")
        return "rejected|\(joined)"
    }
}
