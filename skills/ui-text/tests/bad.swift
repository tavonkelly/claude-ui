struct SettingsView: View {
  var body: some View {
    Form {
      Section("Here you can change your account settings") {
        Toggle("Send me an email every time someone comments on my posts", isOn: $comments)
        Button("OK") { save() }
      }
      Text("Thank you for using our app. We hope you enjoy every single feature we have built.")
    }
    .navigationTitle("Your Account Settings Page Overview")
  }
}
