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
            var findings: [Finding] = []
            var gaps: [String] = []
            var scanned = 0
            var totalBytes = 0
            for path in files {
                do {
                    let input = try FileHandle(forReadingFrom: path)
                    defer { try? input.close() }
                    let data = try input.read(upToCount: 4 * 1024 * 1024 + 1) ?? Data()
                    totalBytes += data.count
                    if data.count > 4 * 1024 * 1024 || totalBytes > 64 * 1024 * 1024 {
                        gaps.append("Source bytes exceed the supported scope limit.")
                        break
                    }
                    guard let source = String(data: data, encoding: .utf8) else {
                        gaps.append("Source could not be read as UTF-8.")
                        continue
                    }
                    findings.append(contentsOf: inspect(path: path.path, source: source))
                    scanned += 1
                } catch {
                    gaps.append("Source could not be read as UTF-8.")
                }
            }
            findings.sort()
            if scanned == 0 && gaps.isEmpty { gaps.append("No supported source files were scanned.") }
            if invocation.json {
                print(try renderReceipt(root: invocation.root.path, scannedFiles: scanned, findings: findings, missingEvidence: gaps))
            } else if findings.isEmpty && gaps.isEmpty {
                print("Pass: \(scanned) Swift files scanned.")
            } else if findings.isEmpty {
                print("Inconclusive: \(Array(Set(gaps)).sorted().joined(separator: "; "))")
            } else {
                for finding in findings {
                    print("\(finding.path):\(finding.line):\(finding.column) \(finding.ruleId) \(finding.message)")
                }
            }
            return !findings.isEmpty ? 1 : !gaps.isEmpty ? 2 : 0
        } catch {
            FileHandle.standardError.write(Data("swift-assay: \(error.localizedDescription)\n".utf8))
            if invocation.json, let receipt = try? renderReceipt(root: invocation.root.path, scannedFiles: 0, findings: [], missingEvidence: ["Source scope is missing, unreadable or unsupported."]) {
                print(receipt)
            }
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
        var ancestor = root
        while true {
            if try ancestor.resourceValues(forKeys: [.isSymbolicLinkKey]).isSymbolicLink != false {
                throw CocoaError(.fileReadUnsupportedScheme)
            }
            let parent = ancestor.deletingLastPathComponent()
            if parent.path == ancestor.path { break }
            ancestor = parent
        }
        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: root.path, isDirectory: &isDirectory), isDirectory.boolValue else {
            throw CocoaError(.fileNoSuchFile)
        }
        var files: [URL] = []
        func visit(_ directory: URL, depth: Int) throws {
            guard depth <= 64 else { throw CocoaError(.fileReadTooLarge) }
            let entries = try FileManager.default.contentsOfDirectory(at: directory,
                includingPropertiesForKeys: [.isSymbolicLinkKey, .isRegularFileKey, .isDirectoryKey])
            for entry in entries.sorted(by: { $0.path < $1.path }) {
                let values = try entry.resourceValues(forKeys: [.isSymbolicLinkKey, .isRegularFileKey, .isDirectoryKey])
                guard values.isSymbolicLink == false else { throw CocoaError(.fileReadUnsupportedScheme) }
                if values.isDirectory == true { try visit(entry, depth: depth + 1) }
                else if entry.pathExtension == "swift" {
                    guard values.isRegularFile == true else { throw CocoaError(.fileReadUnknown) }
                    files.append(entry)
                    guard files.count <= 10_000 else { throw CocoaError(.fileReadTooLarge) }
                }
            }
        }
        try visit(root, depth: 0)
        return files.sorted { $0.path < $1.path }
    }
}
