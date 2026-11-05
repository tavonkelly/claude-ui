import SwiftUI

struct BillingView: View {
    var body: some View {
        VStack(spacing: 10) {
            GroupBox("Plan") {
                GroupBox {
                    Text("Invoices")
                }
            }
            Button("Upgrade") {}.buttonStyle(.borderedProminent)
            Button("Contact sales") {}.buttonStyle(.borderedProminent)
        }
        .padding(13)
    }
}
