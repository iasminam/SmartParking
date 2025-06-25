import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'incorrect_car_page.dart';
import 'departure.dart'; 
import 'login.dart'; 

class DriverPage extends StatefulWidget {
  @override
  _DriverPageState createState() => _DriverPageState();
}

class _DriverPageState extends State<DriverPage> {
  bool _isLoading = false;
  String _message = 'Asteptarea detectiei masinii...';
  String _username = '';

  @override
  void initState() {
    super.initState();
    _fetchUsername();
  }

  Future<void> _fetchUsername() async {
    final prefs = await SharedPreferences.getInstance();
    final username = prefs.getString('username');
    if (username != null) {
      setState(() {
        _username = username;
      });
    } else {
      _performLogout(); // Dacă nu există username, înseamnă că nu e autentificat
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

  // Metoda care va face apelul HTTP POST către Django pentru a declanșa detecția
  Future<void> _triggerCarDetectionFromBackend() async {
    setState(() {
      _isLoading = true;
      _message = 'Se detecteaza masina... te rog asteapta.';
    });

    final prefs = await SharedPreferences.getInstance();
    final accessToken = prefs.getString('access_token');
    // Acesta este endpoint-ul către Django care va executa scriptul SSH pe RPi
    final url = Uri.parse('http://172.20.10.3:8000/api/drivers/trigger_car_detection/');

    if (accessToken == null) {
      _performLogout();
      return;
    }

    try {
      final response = await http.post(
        url,
        headers: {
          'Authorization': 'Bearer $accessToken',
          'Content-Type': 'application/json',
        },
        body: json.encode({}), 
      );

      print('DEBUG: Car Detection Response Status Code: ${response.statusCode}');
      print('DEBUG: Car Detection Response Body: ${response.body}');

      final responseData = jsonDecode(response.body);
      if (response.statusCode == 200) {
        setState(() {
          _message = responseData['message'] ?? 'Detectie reusita si autorizata.';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_message)),
        );
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => DeparturePage()),
        );
      } else {
        setState(() {
          _message = responseData['message'] ?? 'Eroare la detectie sau nr neautorizat.';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_message)),
        );
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => IncorrectCarPage()),
        );
      }
    } catch (e) {
      setState(() {
        _message = 'Eroare de retea la detectia masinii: $e';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Eroare de retea: $e')),
      );
      print('DEBUG: Error in _triggerCarDetectionFromBackend: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Parcare Inteligenta'),
        backgroundColor: Colors.blue,
        automaticallyImplyLeading: false,
        leading: IconButton(
          icon: Icon(Icons.logout, color: Colors.white),
          onPressed: _performLogout,
          tooltip: 'Logout',
        ),
      ),
      body: Center(
        child: _isLoading
            ? CircularProgressIndicator()
            : Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Image.asset(
                      'assets/images/car.jpg', 
                      height: 180,
                    ),
                    SizedBox(height: 20),
                    Text(
                      'Salut, $_username!',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 10),
                    Text(
                      'Apasa pentru a detecta masina si a intra in parcare:',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 16,
                        color: Colors.black87,
                      ),
                    ),
                    SizedBox(height: 24),
                    ElevatedButton(
                      onPressed: _triggerCarDetectionFromBackend, 
                      child: Text('Simuleaza Detectie Masina',
                          style: TextStyle(color: Colors.white)),
                      style: ElevatedButton.styleFrom(
                        padding:
                            EdgeInsets.symmetric(horizontal: 40, vertical: 16),
                        textStyle: TextStyle(fontSize: 18),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(30),
                        ),
                        backgroundColor: Colors.blue,
                      ),
                    ),
                    SizedBox(height: 20),
                    if (_message.isNotEmpty && !_message.contains('Asteptarea'))
                      Text(
                        _message,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 16,
                          color: _message.contains('Eroare') || _message.contains('neautorizata') || _message.contains('nedetectata') ? Colors.red : Colors.green,
                        ),
                      ),
                  ],
                ),
              ),
      ),
    );
  }
}