import Foundation
import SwiftAssay

#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

@main
struct SwiftAssayCLI {
    static func main() {
        exit(Int32(run(arguments: Array(CommandLine.arguments.dropFirst()))))
    }

    private static func run(arguments: [String]) -> Int {
        guard let invocation = parse(arguments: arguments) else {
            FileHandle.standardError.write(Data("usage: swift-assay check <directory> [--json]\n".utf8))
            return 64
        }

        do {
            let files = try sourceFiles(below: invocation.root)
            let findings = try files.flatMap { path in
                inspect(path: path.path, source: try String(contentsOf: path, encoding: .utf8))
            }.sorted()
            if invocation.json {
                print(try renderReceipt(root: invocation.root.path, scannedFiles: files.count, findings: findings))
            } else if findings.isEmpty {
                print("Pass: \(files.count) Swift files scanned.")
            } else {
                for finding in findings {
                    print("\(finding.path):\(finding.line):\(finding.column) \(finding.ruleId) \(finding.message)")
                }
            }
            return findings.isEmpty ? 0 : 1
        } catch {
            FileHandle.standardError.write(Data("swift-assay: \(error.localizedDescription)\n".utf8))
            return 2
        }
    }

    private static func parse(arguments: [String]) -> (root: URL, json: Bool)? {
        guard arguments.count >= 2, arguments[0] == "check" else { return nil }
        let options = Array(arguments.dropFirst(2))
        guard options.allSatisfy({ $0 == "--json" }) else { return nil }
        return (URL(fileURLWithPath: arguments[1], isDirectory: true).standardizedFileURL, options.contains("--json"))
    }

    private static func sourceFiles(below root: URL) throws -> [URL] {
        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: root.path, isDirectory: &isDirectory), isDirectory.boolValue else {
            throw CocoaError(.fileNoSuchFile)
        }
        guard let enumerator = FileManager.default.enumerator(at: root, includingPropertiesForKeys: [.isRegularFileKey]) else {
            throw CocoaError(.fileReadUnknown)
        }
        return enumerator.compactMap { $0 as? URL }
            .filter { $0.pathExtension == "swift" }
            .sorted { $0.path < $1.path }
    }
}
