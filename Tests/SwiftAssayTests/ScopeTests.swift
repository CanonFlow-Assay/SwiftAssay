import Foundation
import Testing
@testable import SwiftAssay

private func withScope(_ body: (URL) throws -> Void) throws {
    let root = FileManager.default.temporaryDirectory.resolvingSymlinksInPath()
        .appendingPathComponent("swift-assay-scope-\(UUID().uuidString)")
    try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
    defer { try? FileManager.default.removeItem(at: root) }
    try body(root)
}

private func invoke(_ root: URL) throws -> (Int32, [String: Any]) {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        .appendingPathComponent(".build/debug/swift-assay")
    process.arguments = ["check", root.path, "--json"]
    let output = Pipe(); let errors = Pipe()
    process.standardOutput = output; process.standardError = errors
    try process.run(); process.waitUntilExit()
    let data = output.fileHandleForReading.readDataToEndOfFile()
    return (process.terminationStatus, try #require(JSONSerialization.jsonObject(with: data) as? [String: Any]))
}

@Test func emptyAndMissingSourceCannotPass() throws {
    try withScope { root in
        for path in [root, root.appendingPathComponent("missing")] {
            let (code, receipt) = try invoke(path)
            #expect(code == 2)
            #expect(receipt["verdict"] as? String == "Inconclusive")
        }
    }
}

@Test func linkedSourceScopesCannotPass() throws {
    try withScope { root in
        let source = root.appendingPathComponent("source")
        let outside = root.appendingPathComponent("outside")
        try FileManager.default.createDirectory(at: source, withIntermediateDirectories: false)
        try FileManager.default.createDirectory(at: outside, withIntermediateDirectories: false)
        let file = outside.appendingPathComponent("good.swift")
        try Data("let value = 1\n".utf8).write(to: file)
        for (name, target) in [("linked.swift", file), ("directory", outside)] {
            let link = source.appendingPathComponent(name)
            try FileManager.default.createSymbolicLink(at: link, withDestinationURL: target)
            #expect(try invoke(source).0 == 2)
            try FileManager.default.removeItem(at: link)
        }
        let rootLink = root.appendingPathComponent("linked-root")
        try FileManager.default.createSymbolicLink(at: rootLink, withDestinationURL: outside)
        #expect(try invoke(rootLink).0 == 2)
    }
}

@Test func malformedSourceDoesNotEraseKnownFindings() throws {
    try withScope { root in
        try Data([0xff]).write(to: root.appendingPathComponent("invalid.swift"))
        #expect(try invoke(root).0 == 2)
        try Data("fatalError(\"bad\")\n".utf8).write(to: root.appendingPathComponent("bad.swift"))
        let (code, receipt) = try invoke(root)
        #expect(code == 1)
        #expect(receipt["verdict"] as? String == "Fail")
        #expect(receipt["missingEvidence"] != nil)
    }
}

@Test func nonemptySourceRetainsOldExitMeanings() throws {
    try withScope { root in
        let source = root.appendingPathComponent("domain.swift")
        try Data("let value = 1\n".utf8).write(to: source)
        #expect(try invoke(root).0 == 0)
        try Data("fatalError(\"bad\")\n".utf8).write(to: source)
        #expect(try invoke(root).0 == 1)
    }
}

@Test func zeroObservedFilesNeverRenderPass() throws {
    #expect(try renderReceipt(root: "empty", scannedFiles: 0, findings: []).contains("Inconclusive"))
}
