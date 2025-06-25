import 'package:flutter/material.dart';
import 'welcome.dart';
import 'register.dart';
import 'login.dart';
import 'driver.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_stripe/flutter_stripe.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SharedPreferences prefs = await SharedPreferences.getInstance();
  String? accessToken = prefs.getString('access_token');
  Stripe.publishableKey = 'pk_test_51QyZRcE69IsaXt9Zt9SLFiNt9ZuJ1OEQgeXsDhfxHYyIM088O166fiIXde3brSKJ5b7ETnND24z8tu130kwB9Q3R00xX5hZRsu';

   runApp(MyApp(initialRoute: accessToken != null ? '/driver' : '/'));
}

class MyApp extends StatelessWidget {
  final String initialRoute;

  const MyApp({Key? key, required this.initialRoute}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Parking',
      initialRoute: initialRoute,
      routes: {
        '/': (context) => WelcomePage(), 
        '/register': (context) => RegisterPage(),
        '/login': (context) => LoginPage(),
        '/driver': (context) => DriverPage(),
     },
    );
  }
}