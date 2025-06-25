import 'package:flutter/material.dart';
import 'package:http/http.dart' as http; 
import 'dart:convert'; 
import 'package:shared_preferences/shared_preferences.dart'; 
import 'driver.dart'; 

class PaymentSuccessPage extends StatefulWidget {
  final double totalCost;

  const PaymentSuccessPage({Key? key, required this.totalCost}) : super(key: key);

  @override
  _PaymentSuccessPageState createState() => _PaymentSuccessPageState();
}

class _PaymentSuccessPageState extends State<PaymentSuccessPage> {
  bool _isLoading = false; // Stare pentru a indica dacă se efectuează un apel API
  String? _errorMessage;
  String _statusMessage = 'Plata a fost efectuată cu succes!';
  bool _departureConfirmed = false; // Stare pentru a ține evidența confirmării plecării

  @override
  void initState() {
    super.initState();
  }

  Future<void> _verifyDeparture() async {
    setState(() {
      _isLoading = true; // Setăm starea de încărcare
      _errorMessage = null; // Resetăm orice mesaj de eroare anterior
      _statusMessage = 'Verificarea plecării. Vă rugăm așteptați la barieră...';
    });

    final prefs = await SharedPreferences.getInstance();
    final String? accessToken = prefs.getString('access_token');
    final String baseUrl = 'http://172.20.10.3:8000/api'; 

    if (accessToken == null) {
      setState(() {
        _errorMessage = 'Eroare: Nu ești autentificat.';
        _isLoading = false;
        _statusMessage = 'Eroare la plecare.';
      });
      return;
    }

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/drivers/verify_departure/'), // Endpoint-ul nou pentru ieșire
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $accessToken',
        },
      );

      final responseData = json.decode(response.body);

      if (response.statusCode == 200) {
        // Succes: Bariera s-a deschis și starea driverului a fost resetată
        setState(() {
          _statusMessage = responseData['message'] ?? 'Plecare confirmată cu succes!';
          _departureConfirmed = true;
          _errorMessage = null;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_statusMessage))
        );
        // După o scurtă pauză pentru a permite utilizatorului să citească mesajul, navigăm la DriverPage
        Future.delayed(Duration(seconds: 2), () {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(builder: (context) => DriverPage()),
          );
        });
      } else {
        // Eroare de la backend
        setState(() {
          _errorMessage = responseData['detail'] ?? 'A apărut o eroare la confirmarea plecării.';
          _statusMessage = 'Eroare la plecare.';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_errorMessage!))
        );
      }
    } catch (e) {
      // Eroare de rețea sau altă excepție
      setState(() {
        _errorMessage = 'Eroare de rețea: Nu se poate conecta la server. Verificați conexiunea.';
        _statusMessage = 'Eroare la plecare.';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_errorMessage!))
      );
    } finally {
      setState(() {
        _isLoading = false; // Oprim starea de încărcare indiferent de rezultat
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Plată Reușită'),
        backgroundColor: Colors.blue,
        automaticallyImplyLeading: false, // Nu afișăm butonul de întoarcere implicit
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: <Widget>[
              // Afișăm un indicator de încărcare sau o pictogramă de succes
              _isLoading
                  ? CircularProgressIndicator(
                      color: Colors.blue,
                    )
                  : Icon(
                      Icons.check_circle_outline,
                      color: Colors.green,
                      size: 100.0,
                    ),
              SizedBox(height: 20.0),
              Text(
                _statusMessage, 
                style: TextStyle(
                  fontSize: 24.0,
                  fontWeight: FontWeight.bold,
                  color: _errorMessage != null ? Colors.red : Colors.green, 
                ),
                textAlign: TextAlign.center,
              ),
              SizedBox(height: 10.0),
              // Afișează suma doar dacă nu e eroare, nu e încărcare ȘI plecarea NU a fost confirmată
              if (!_isLoading && _errorMessage == null && !_departureConfirmed) 
                Text(
                  'Suma plătită: ${widget.totalCost.toStringAsFixed(2)} RON',
                  style: TextStyle(
                    fontSize: 18.0,
                    color: Colors.black87,
                  ),
                  textAlign: TextAlign.center,
                ),
              SizedBox(height: 30.0),
              if (!_isLoading && !_departureConfirmed)
                ElevatedButton(
                  onPressed: _verifyDeparture, // Aici apelăm funcția pentru a verifica plecarea
                  child: Text('Simulează Plecarea', style: TextStyle(color: Colors.black)),
                  style: ElevatedButton.styleFrom(
                    padding: EdgeInsets.symmetric(horizontal: 40, vertical: 16),
                    textStyle: TextStyle(fontSize: 18),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(30),
                    ),
                    backgroundColor: Colors.blue,
                  ),
                ),
              SizedBox(height: 10.0),
              // Afișează mesajul de eroare dacă există
              if (_errorMessage != null)
                Text(
                  _errorMessage!,
                  style: TextStyle(color: Colors.red, fontSize: 16),
                  textAlign: TextAlign.center,
                ),
            ],
          ),
        ),
      ),
    );
  }
}