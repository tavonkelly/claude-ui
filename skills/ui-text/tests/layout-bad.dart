import 'package:flutter/material.dart';

class Billing extends StatelessWidget {
  const Billing({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(13),
      child: Card(
        child: Column(children: [
          Card(child: Text('Invoices')),
          FilledButton(onPressed: () {}, child: const Text('Upgrade')),
          FilledButton(onPressed: () {}, child: const Text('Contact sales')),
        ]),
      ),
    );
  }
}
