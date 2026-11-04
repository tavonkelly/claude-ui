Widget build(BuildContext context) {
  final key = 'orders_list';
  return Column(children: [
    Text('Orders'),
    TextField(decoration: InputDecoration(labelText: 'Email', hintText: 'name@example.com')),
    ElevatedButton(onPressed: placeOrder, child: const Text('Place order')),
    Text('${orders.length} orders'),
    SnackBar(content: Text('Order placed')),
  ]);
}
