import 'package:flutter/material.dart';
import 'package:flutter_stripe/flutter_stripe.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'payment_success_page.dart';
import 'driver.dart';

class PaymentPage extends StatefulWidget {
  const PaymentPage({Key? key}) : super(key: key);

  @override
  _PaymentPageState createState() => _PaymentPageState();
}

class _PaymentPageState extends State<PaymentPage> {
  bool _isLoading = false;
  String? _message; // Mesaj de eroare sau succes
  double _totalCost = 0.0; // Va stoca costul total calculat de backend
  String? _clientSecret; // Va stoca clientSecret-ul de la backend
  String? _paymentStatus; // Va stoca statusul plății
  String? _paymentIntentId; // va stoca PaymentIntentId-ul

  @override
  void initState() {
    super.initState();
    // Inițializează procesul de plecare pentru a obține costul și clientSecret-ul
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _simulateDepartureProcess();
    });
  }

  Future<void> _simulateDepartureProcess() async {
    setState(() {
      _isLoading = true;
      _message = 'Calculăm costul parcării...';
      _totalCost = 0.0;
      _clientSecret = null;
      _paymentStatus = null;
      _paymentIntentId = null; 
    });

    final prefs = await SharedPreferences.getInstance();
    final String? accessToken = prefs.getString('access_token');
    final String baseUrl = 'http://172.20.10.3:8000/api';

    if (accessToken == null) {
      setState(() {
        _message = 'Eroare: Nu ești autentificat. Te rugăm să te autentifici din nou.';
        _isLoading = false;
      });
      return;
    }

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/drivers/simulate_departure/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $accessToken',
        },
      );

      final responseData = json.decode(response.body);

      if (response.statusCode == 200) {
        setState(() {
          _totalCost = (responseData['total_cost'] as num).toDouble();
          _clientSecret = responseData['clientSecret'];
          _paymentStatus = responseData['payment_status'];
          _paymentIntentId = responseData['payment_intent_id']; 
          if (_clientSecret != null && _clientSecret!.contains('_secret_')) {
            _paymentIntentId = _clientSecret!.split('_secret_')[0];
          }

        });

        if (_paymentStatus == 'free') {
          // Caz: Parcare gratuită
          setState(() {
            _message = 'Parcare gratuită! Nu este necesară plata.';
          });
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Parcare gratuită! Ieșirea este permisă.')),
          );
          // Navigăm direct la PaymentSuccessPage pentru a simula plecarea
          Future.delayed(const Duration(seconds: 1), () {
            Navigator.pushReplacement(
              context,
              MaterialPageRoute(builder: (context) => PaymentSuccessPage(totalCost: _totalCost)),
            );
          });
        } else if (_paymentStatus == 'pending_payment' && _clientSecret != null) {
          // Caz: Plata necesară, inițializăm Payment Sheet
          setState(() {
            _message = 'Plata este necesară. Suma: ${_totalCost.toStringAsFixed(2)} RON';
          });
          await _initPaymentSheet(); // Inițializează PaymentSheet după ce avem clientSecret
        } else {
          // Un caz neașteptat 
          setState(() {
            _message = 'Eroare: Răspuns neașteptat de la server privind plata.';
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(_message!)),
          );
        }
      } else {
        setState(() {
          _message = responseData['detail'] ?? 'Eroare la calcularea costului parcării.';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_message!)),
        );
      }
    } catch (e) {
      setState(() {
        _message = 'Eroare de rețea sau internă: ${e.toString()}';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_message!)),
      );
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _initPaymentSheet() async {
    // Verificăm dacă _clientSecret este valid înainte de a inițializa
    if (_clientSecret == null) {
      setState(() {
        _message = 'Eroare: Client Secret invalid pentru inițializarea plății.';
      });
      return;
    }

    try {
      await Stripe.instance.initPaymentSheet(
        paymentSheetParameters: SetupPaymentSheetParameters(
          paymentIntentClientSecret: _clientSecret!, // Folosim clientSecret obținut
          merchantDisplayName: 'Smart Parking', 
          style: ThemeMode.light,
        ),
      );
      setState(() {
        _message = 'Payment Sheet inițializat. Apasă "Plătește" pentru a continua.';
      });
    } catch (e) {
      setState(() {
        _message = 'Eroare la inițializarea Payment Sheet: $e';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Eroare: $e')),
      );
      print('DEBUG: PaymentPage - Init Payment Sheet Error: $e');
      // În cazul unei erori la inițializare, întoarcem utilizatorul
      Navigator.pop(context);
    }
  }

  // Funcția pentru a confirma plata cu backend-ul
  Future<bool> _confirmPaymentWithBackend(String paymentIntentId) async {
    final prefs = await SharedPreferences.getInstance();
    final String? accessToken = prefs.getString('access_token');
    final String baseUrl = 'http://172.20.10.3:8000/api';

    if (accessToken == null) {
      print('Eroare la confirm_payment: Nu ești autentificat.');
      return false;
    }

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/drivers/confirm-payment/'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $accessToken',
        },
        body: json.encode({'paymentIntentId': paymentIntentId}),
      );

      if (response.statusCode == 200) {
        print('Backend a confirmat plata pentru PaymentIntent ID: $paymentIntentId');
        return true;
      } else {
        final errorData = json.decode(response.body);
        print('Eroare la confirmarea plății cu backend-ul (${response.statusCode}): ${errorData['detail'] ?? response.body}');
        return false;
      }
    } catch (e) {
      print('Eroare de rețea la apelul confirm_payment: $e');
      return false;
    }
  }

  Future<void> _displayPaymentSheet() async {
    setState(() {
      _isLoading = true;
      _message = 'Procesare plată...';
    });

    try {
      await Stripe.instance.presentPaymentSheet();
      // Dacă ajungem aici, plata a fost prezentată și, cel mai probabil, reușită de utilizator.
      String? actualPaymentIntentId = _paymentIntentId;
      if (actualPaymentIntentId == null && _clientSecret != null && _clientSecret!.contains('_secret_')) {
          actualPaymentIntentId = _clientSecret!.split('_secret_')[0];
      }

      if (actualPaymentIntentId != null) {
        final bool confirmed = await _confirmPaymentWithBackend(actualPaymentIntentId);
        if (confirmed) {
          setState(() {
            _message = 'Plata a fost finalizată și confirmată cu succes!';
          });
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Plată efectuată și confirmată cu succes!')),
          );
          // După plată reușită și confirmare, navigăm la PaymentSuccessPage
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(builder: (context) => PaymentSuccessPage(totalCost: _totalCost)),
          );
        } else {
          // Backend-ul nu a confirmat plata
          setState(() {
            _message = 'Plată reușită local, dar nu a putut fi confirmată de server. Vă rugăm reîncercați sau contactați suportul.';
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(_message!)),
          );
          // Rămânem pe pagina de plată sau navigăm la o pagină de eroare
        }
      } else {
        setState(() {
          _message = 'Eroare: Nu s-a putut obține PaymentIntent ID pentru confirmare.';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_message!)),
        );
      }
    } on StripeException catch (e) {
      if (e.error.code == FailureCode.Canceled) {
        setState(() {
          _message = 'Plata a fost anulată de utilizator.';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Plata a fost anulată.')),
        );
      } else {
        setState(() {
          _message = 'Eroare la procesarea plății: ${e.error.message}';
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Eroare de plată: ${e.error.message}')),
        );
        print('DEBUG: PaymentPage - Payment Sheet Error: ${e.error.message}');
      }
    } catch (e) {
      setState(() {
        _message = 'Eroare neașteptată la afișarea Payment Sheet: $e';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Eroare: $e')),
      );
      print('DEBUG: PaymentPage - Unexpected Error: $e');
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false, // Împiedică utilizatorul să dea back cu butonul de sistem
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Plată Parcare'),
          backgroundColor: Colors.green,
          automaticallyImplyLeading: false, // Ascunde butonul de back din AppBar
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Image.asset(
                  'assets/images/pay.png',
                  height: 150.0,
                ),
                const SizedBox(height: 30.0),
                Text(
                  _message ?? 'Așteptați...', 
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 20,
                    color: _message != null && _message!.contains('Eroare') ? Colors.red : Colors.black87,
                  ),
                ),
                const SizedBox(height: 10.0),
                if (_totalCost > 0 && _paymentStatus == 'pending_payment' && !_isLoading) // Afișăm suma doar dacă e de plătit
                  Text(
                    'Suma de plată: ${_totalCost.toStringAsFixed(2)} RON',
                    style: TextStyle(fontSize: 36, fontWeight: FontWeight.bold, color: Colors.green[800]),
                  ),
                const SizedBox(height: 40.0),
                _isLoading
                    ? const CircularProgressIndicator()
                    : _clientSecret != null && _totalCost > 0 && _paymentStatus == 'pending_payment'
                        ? ElevatedButton(
                            onPressed: _displayPaymentSheet,
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 50, vertical: 18),
                              textStyle: const TextStyle(fontSize: 20),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(30),
                              ),
                              backgroundColor: Colors.green,
                            ),
                            child: const Text('Plătește Acum', style: TextStyle(color: Colors.white)),
                          )
                        : _paymentStatus == 'free'
                            ? Column(
                                children: [
                                  const Text(
                                    'Puteți apăsa "Simulează Plecarea" acum.',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(fontSize: 18, color: Colors.black87),
                                  ),
                                  const SizedBox(height: 20),
                                  ElevatedButton(
                                    onPressed: () {
                                      // Navigăm direct la PaymentSuccessPage, pentru că plata nu e necesară
                                      Navigator.pushReplacement(
                                        context,
                                        MaterialPageRoute(builder: (context) => PaymentSuccessPage(totalCost: 0.00)),
                                      );
                                    },
                                    style: ElevatedButton.styleFrom(
                                      padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 16),
                                      textStyle: const TextStyle(fontSize: 18),
                                      shape: RoundedRectangleBorder(
                                        borderRadius: BorderRadius.circular(30),
                                      ),
                                      backgroundColor: Colors.blue,
                                    ),
                                    child: const Text('Simulează Plecarea', style: TextStyle(color: Colors.black)),
                                  ),
                                ],
                              )
                            : ElevatedButton(
                                // Buton pentru a reîncerca dacă există o eroare
                                onPressed: _simulateDepartureProcess,
                                style: ElevatedButton.styleFrom(
                                  padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 16),
                                  textStyle: const TextStyle(fontSize: 18),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(30),
                                  ),
                                  backgroundColor: Colors.orange,
                                ),
                                child: const Text('Reîncearcă', style: TextStyle(color: Colors.white)),
                              ),
                const SizedBox(height: 20.0),
                // Dacă există un mesaj de eroare și nu sunt butoane dedicate, afișăm aici
                if (_message != null && (_clientSecret == null || _totalCost == 0) && _paymentStatus != 'free')
                  Text(
                    _message!,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: _message!.contains('Eroare') ? Colors.red : Colors.blue,
                      fontSize: 16,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}