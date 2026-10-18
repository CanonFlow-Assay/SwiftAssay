import Foundation

func loadOrder() -> String {
    let value = try! String(contentsOfFile: "order.txt")
    print("loaded")
    return value
}
