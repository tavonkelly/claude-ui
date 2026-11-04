struct SettingsView: View {
  var body: some View {
    Form {
      Section("Account") {
        Toggle("Comments", isOn: $comments)
        Button("Save changes") { save() }
      }
      Text("\(count) devices")
    }
    .navigationTitle("Settings")
    .alert("Delete 3 events?", isPresented: $confirm) {
      Button("Delete events", role: .destructive) { delete() }
      Button("Cancel", role: .cancel) {}
    } message: {
      Text("This cannot be undone.")
    }
  }
  let id = "settings-view"
}
