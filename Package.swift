// swift-tools-version: 6.4
import PackageDescription

let package = Package(
    name: "SwiftAssay",
    products: [
        .library(name: "SwiftAssay", targets: ["SwiftAssay"]),
        .executable(name: "swift-assay", targets: ["SwiftAssayCLI"]),
    ],
    targets: [
        .target(name: "SwiftAssay"),
        .executableTarget(name: "SwiftAssayCLI", dependencies: ["SwiftAssay"]),
        .testTarget(name: "SwiftAssayTests", dependencies: ["SwiftAssay"]),
    ],
    swiftLanguageModes: [.v6]
)
