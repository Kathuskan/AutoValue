import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const ValuationApp());
}

class ValuationApp extends StatelessWidget {
  const ValuationApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Car Valuation Engine',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: const ValuationScreen(),
    );
  }
}

class ValuationScreen extends StatefulWidget {
  const ValuationScreen({Key? key}) : super(key: key);

  @override
  _ValuationScreenState createState() => _ValuationScreenState();
}

class _ValuationScreenState extends State<ValuationScreen> {
  final _formKey = GlobalKey<FormState>();
  
  // Form input controllers
  final TextEditingController brandCtrl = TextEditingController(text: 'TOYOTA');
  final TextEditingController modelCtrl = TextEditingController(text: 'Corolla');
  final TextEditingController yomCtrl = TextEditingController(text: '2015');
  final TextEditingController engineCtrl = TextEditingController(text: '1500');
  final TextEditingController gearCtrl = TextEditingController(text: 'Automatic');
  final TextEditingController fuelCtrl = TextEditingController(text: 'Petrol');
  final TextEditingController millageCtrl = TextEditingController(text: '80000');
  final TextEditingController townCtrl = TextEditingController(text: 'Colombo');
  final TextEditingController conditionCtrl = TextEditingController(text: 'USED');

  String predictedPrice = "";
  bool isLoading = false;

  Future<void> fetchPrediction() async {
    if (!_formKey.currentState!.validate()) return;
    
    setState(() { isLoading = true; });

    // Use 10.0.2.2 for Android Emulator connecting to local host, or localhost/127.0.0.1 for iOS
    final url = Uri.parse('http://127.0.0.1:8000/predict'); 
    
    try {
      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "brand": brandCtrl.text,
          "model_name": modelCtrl.text,
          "yom": int.parse(yomCtrl.text),
          "engine_cc": double.parse(engineCtrl.text),
          "gear": gearCtrl.text,
          "fuel_type": fuelCtrl.text,
          "millage": double.parse(millageCtrl.text),
          "town": townCtrl.text,
          "condition": conditionCtrl.text
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          predictedPrice = "Estimated Price: ${data['predicted_price_lkr']} LKR (Lakhs)";
        });
      } else {
        setState(() { predictedPrice = "Error: Failed to fetch prediction"; });
      }
    } catch (e) {
      setState(() { predictedPrice = "Connection Error. Is API running?"; });
    } finally {
      setState(() { isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Car Valuation Engine')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: ListView(
            children: [
              TextFormField(controller: brandCtrl, decoration: const InputDecoration(labelText: 'Brand')),
              TextFormField(controller: modelCtrl, decoration: const InputDecoration(labelText: 'Model')),
              TextFormField(controller: yomCtrl, decoration: const InputDecoration(labelText: 'Year of Manufacture')),
              TextFormField(controller: engineCtrl, decoration: const InputDecoration(labelText: 'Engine Capacity (cc)')),
              TextFormField(controller: gearCtrl, decoration: const InputDecoration(labelText: 'Gear (Automatic/Manual)')),
              TextFormField(controller: fuelCtrl, decoration: const InputDecoration(labelText: 'Fuel Type')),
              TextFormField(controller: millageCtrl, decoration: const InputDecoration(labelText: 'Mileage (KM)')),
              TextFormField(controller: townCtrl, decoration: const InputDecoration(labelText: 'Town')),
              TextFormField(controller: conditionCtrl, decoration: const InputDecoration(labelText: 'Condition (USED/Brand New)')),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: fetchPrediction,
                child: isLoading ? const CircularProgressIndicator(color: Colors.white) : const Text('Predict Price'),
              ),
              const SizedBox(height: 20),
              Text(
                predictedPrice, 
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              )
            ],
          ),
        ),
      ),
    );
  }
}