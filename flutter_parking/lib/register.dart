import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/intl.dart';

class RegisterPage extends StatefulWidget {
  @override
  _RegisterPageState createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _driverNameController = TextEditingController();
  final _carNumberPlateController = TextEditingController();
  bool _isLoading = false;

  Future<void> _register() async {
    if (_formKey.currentState!.validate()) {
      setState(() {
        _isLoading = true;
      });

      final url = Uri.parse('http://172.20.10.3:8000/api/drivers/register/');
      final requestBody = jsonEncode({
        'username': _usernameController.text,
        'password': _passwordController.text,
        'driver_name': _driverNameController.text,
        'car_number_plate': _carNumberPlateController.text,
      });

      try {
        final response = await http.post(
          url,
          body: requestBody,
          headers: {'Content-Type': 'application/json'},
        );

        if (response.statusCode == 201) {
          final data = jsonDecode(response.body);

          final loginUrl = Uri.parse('http://172.20.10.3:8000/api/drivers/login/'); // automat login 
          final loginRequestBody = jsonEncode({
            'username': _usernameController.text,
            'password': _passwordController.text,
          });

          try {
            final loginResponse = await http.post(
              loginUrl,
              body: loginRequestBody,
              headers: {'Content-Type': 'application/json'},
            );

            if (loginResponse.statusCode == 200) {
              final loginData = jsonDecode(loginResponse.body);
              final accessToken = loginData['access'];
              final refreshToken = loginData['refresh'];
              final driverName = loginData['driver_name']; 
              final userName = loginData['username'];

              final prefs = await SharedPreferences.getInstance();
              await prefs.setString('access_token', accessToken);
              await prefs.setString('refresh_token', refreshToken);
              await prefs.setString('driver_name', driverName);
              await prefs.setString('username', userName);

              Navigator.pushReplacementNamed(context, '/driver'); 
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                    content: Text('Registration and login successful')),
              );
            } else {
              print('Login Error: ${loginResponse.statusCode}');
              print('Login Response body: ${loginResponse.body}');
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                    content: Text(
                        'Registration successful, but login failed: ${loginResponse.body}')),
              );
            }
          } catch (loginError) {
            print('Login Error: $loginError');
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                  content: Text(
                      'Registration successful, but login failed: $loginError')),
            );
          }
        } else {
          print('Registration Error: ${response.statusCode}');
          print('Registration Response Body: ${response.body}');
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Registration failed: ${response.body}')),
          );
        }
      } catch (e) {
        print('Error: $e');
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('An error occurred')),
        );
      } finally {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Register'),
        backgroundColor: Colors.blue, 
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16.0),
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: <Widget>[
                Image.asset(
                  'assets/images/car.jpg', 
                  height: 180,
                ),
                SizedBox(height: 20),
                TextFormField(
                  controller: _usernameController,
                  decoration: InputDecoration(
                    labelText: 'Username',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10.0),
                    ),
                    filled: true,
                    fillColor: Colors.grey[200],
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter a username';
                    }
                    return null;
                  },
                ),
                SizedBox(height: 16),
                TextFormField(
                  controller: _passwordController,
                  decoration: InputDecoration(
                    labelText: 'Password',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10.0),
                    ),
                    filled: true,
                    fillColor: Colors.grey[200],
                  ),
                  obscureText: true,
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter a password';
                    }
                    return null;
                  },
                ),
                SizedBox(height: 16),
                TextFormField(
                  controller: _driverNameController,
                  decoration: InputDecoration(
                    labelText: 'Driver Name',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10.0),
                    ),
                    filled: true,
                    fillColor: Colors.grey[200],
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter driver name';
                    }
                    return null;
                  },
                ),
                SizedBox(height: 16),
                TextFormField(
                  controller: _carNumberPlateController,
                  decoration: InputDecoration(
                    labelText: 'Car Number Plate',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10.0),
                    ),
                    filled: true,
                    fillColor: Colors.grey[200],
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter car number plate';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 20),
                ElevatedButton(
                  onPressed: _isLoading ? null : _register,
                  child: _isLoading
                      ? const CircularProgressIndicator()
                      : const Text('Register', style: TextStyle(color: Colors.black)),
                  style: ElevatedButton.styleFrom(
                    padding: EdgeInsets.symmetric(horizontal: 40, vertical: 16),
                    textStyle: TextStyle(fontSize: 18),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(30),
                    ),
                    backgroundColor: Colors.blue, 
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