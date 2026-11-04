Widget build(BuildContext context) {
  return Column(children: [
    Text('Welcome! This screen lets you see every order you have placed with us so far.'),
    TextField(decoration: InputDecoration(labelText: 'Enter your email', hintText: 'Please use your work address')),
    ElevatedButton(onPressed: submit, child: const Text('Submit')),
    Tooltip(message: 'Oops, something went wrong', child: icon),
  ]);
}
