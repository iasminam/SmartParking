import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'payment_page.dart';
import 'payment_success_page.dart';
import 'driver.dart'; 
import 'login.dart'; 

class DeparturePage extends StatefulWidget {
  @override
  _DeparturePageState createState() => _DeparturePageState();
}

class _DeparturePageState extends State<DeparturePage> {
  bool _isLoading = false;
  String? _message; // Mesaj pentru utilizator

  @override
  void initState() {
    super.initState();
  }

  // Această funcție va fi apelată când șoferul vrea să plece
  Future<void> _initiateDepartureProcess() async {
    setState(() {
      _isLoading = true;
      _message = 'Se pregătește procesul de plecare...';
    });

    final prefs = await SharedPreferences.getInstance();
    final accessToken = prefs.getString('access_token');
    final url = Uri.parse('http://172.20.10.3:8000/api/drivers/simulate_departure/');

    if (accessToken == null) {
      _performLogout(); // Redirecționăm la login dacă nu există token
      return;
    }

    try {
      final response = await http.post(
        url,
        headers: {
          'Authorization': 'Bearer $accessToken',
          'Content-Type': 'application/json',
        },
      );

      print('DEBUG: DeparturePage - Simulate Departure Response Status Code: ${response.statusCode}');
      print('DEBUG: DeparturePage - Simulate Departure Response Body: ${response.body}');

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        final double totalCost = (responseData['total_cost'] as num?)?.toDouble() ?? 0.0;
        final String? clientSecret = responseData['clientSecret']; 
        final String detailMessage = responseData['detail'] ?? 'Suma de plată calculată.';

        setState(() {
          _message = detailMessage;
        });

        if (totalCost > 0 && clientSecret != null) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Plata necesară: ${totalCost.toStringAsFixed(2)} RON. Se deschide pagina de plată.')),
          );
          // Navigăm la PaymentPage, pasându-i suma de plată ȘI clientSecret-ul
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (ctx) => const PaymentPage(),
            ),
          ).then((paymentSuccessful) {
            // Când PaymentPage se închide, verificăm rezultatul
            if (paymentSuccessful == true) {
              // Dacă plata a fost un succes, navigăm la PaymentSuccessPage
              Navigator.pushReplacement(
                context,
                MaterialPageRoute(
                  builder: (ctx) => PaymentSuccessPage(
                    totalCost: totalCost, 
                  ),
                ),
              );
            } else {
              // Dacă plata a fost anulată sau a eșuat, rămânem pe DeparturePage
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Plata a fost anulată sau a eșuat.')),
              );
            }
          }); 

        } else if (totalCost == 0) {
          // Cazul în care suma de plată este 0 (parcare gratuită, abonament etc.)
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Parcare gratuită. Plecare înregistrată.')),
          );
          // Navigăm direct la PaymentSuccessPage pentru a confirma plecarea fără plată
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (ctx) => PaymentSuccessPage(
                totalCost: 0.0,
              ),
            ),
          );
        } else {
          // Cazul în care suma > 0 dar clientSecret este null (eroare în backend)
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Eroare: Nu s-a putut obține clientSecret pentru plată.')),
          );
        }

      } else {
        final errorDetail = jsonDecode(response.body)['detail'] ?? 'Eroare necunoscută.';
        setState(() {
          _message = 'Eroare la procesarea plecării: $errorDetail';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text('Eroare la plecare: ${response.statusCode} - $errorDetail')),
        );
      }
    } catch (e) {
      setState(() {
        _message = 'Eroare de conexiune la plecare: $e';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Eroare de rețea la plecare: $e')),
      );
      print('DEBUG: Error in _initiateDepartureProcess: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _performLogout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('username');
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (context) => LoginPage()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Parcare Activă'),
        backgroundColor: Colors.blue,
        automaticallyImplyLeading: false, // Nu afișăm butonul de back
        leading: IconButton(
          icon: Icon(Icons.logout, color: Colors.white),
          onPressed: _performLogout,
          tooltip: 'Logout',
        ),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Image.asset(
                'assets/images/activ.png', 
                height: 180.0,
              ),
              SizedBox(height: 30.0),
              Text(
                'Bun venit în parcare!',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: Colors.blue,
                ),
                textAlign: TextAlign.center,
              ),
              SizedBox(height: 10.0),
              Text(
                'Acum poți parca. Când dorești să pleci, apasă butonul de mai jos.',
                style: TextStyle(
                  fontSize: 16,
                  color: Colors.black87,
                ),
                textAlign: TextAlign.center,
              ),
              SizedBox(height: 40),
              _isLoading
                  ? CircularProgressIndicator()
                  : ElevatedButton(
                      onPressed: _initiateDepartureProcess, // Apelăm funcția de plecare
                      child: Text('Simulează Plecare și Plata', style: TextStyle(color: Colors.white)),
                      style: ElevatedButton.styleFrom(
                        padding: EdgeInsets.symmetric(horizontal: 40, vertical: 16),
                        textStyle: TextStyle(fontSize: 18),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(30),
                        ),
                        backgroundColor: Colors.blue,
                      ),
                    ),
              if (_message != null && _message!.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 20.0),
                  child: Text(
                    _message!,
                    style: TextStyle(color: Colors.red, fontSize: 16),
                    textAlign: TextAlign.center,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}