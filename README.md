# SmartParking

Pași pentru Crearea și Configurarea Aplicației 

Crearea Proiectului Django:
Trebuie Python și pip instalate.

Instalare Django și Django REST Framework:
pip install Django djangorestframework

Creeare nou proiect Django:
django-admin startproject smart_parking_backend
cd smart_parking_backend

Creeare aplicație Django în cadrul proiectului:
python manage.py startapp core  # Sau numele dorit pentru aplicație

Configurarea Bazei de Date:
Baza de date implicită Django este SQLite, care este suficientă pentru dezvoltare. Configurarea se face în smart_parking_backend/settings.py.

Aplicarea Migrărilor Inițiale:
python manage.py makemigrations
python manage.py migrate

Crearea unui Superuser
Pentru a accesa interfața de administrare Django:
python manage.py createsuperuser

Instalarea Dependențelor Specifice Backend-ului:
Instalează pachetele necesare pentru OCR (dacă faci procesarea pe backend), Stripe, SSH (Paramiko) etc.
pip install Pillow django-rest-framework stripe paramiko 


Crearea și Configurarea Aplicației Mobile (Flutter)
Instalarea Flutter SDK:

Descarcă Flutter SDK de pe site-ul oficial Flutter.

Dezarhivează-l într-un director, de exemplu, C:\src\flutter (Windows) sau ~/flutter (Linux/macOS).

Adaugă calea către directorul bin al Flutter la variabila de mediu PATH.

Verifică instalarea:
flutter doctor


Instalarea Android Studio și SDK-ului Android:

Descarcă și instalează Android Studio.

În Android Studio, navighează la SDK Manager (Tools -> SDK Manager) și asigură-te că ai instalat Android SDK Platform pentru o versiune recentă (ex: Android 13/14) și Android SDK Command-line Tools.

Asigură-te că ai cel puțin un Android Virtual Device (AVD) configurat pentru a rula emulatorul. Poți crea unul din AVD Manager în Android Studio.

Crearea Proiectului Flutter:
flutter create smart_parking_app
cd smart_parking_app

Adăugarea Dependențelor Flutter:

Deschide fișierul pubspec.yaml și adaugă dependențele necesare pentru HTTP requests, stocare locală (Shared Preferences), UI/UX, etc.

dependencies:
  flutter:
    sdk: flutter
  http: ^x.y.z # pentru apeluri HTTP la backend
  shared_preferences: ^a.b.c # pentru stocarea token-urilor

Rulează pentru a instala dependențele: flutter pub get

Configurarea Sistemului Raspberry Pi
Instalarea Raspberry Pi OS:

Descarcă imaginea Raspberry Pi OS (Legacy sau Desktop) de pe site-ul oficial Raspberry Pi.

Utilizează Raspberry Pi Imager pentru a scrie imaginea pe un card microSD (minim 8GB, recomandat 16GB+).

Asigură-te că activezi SSH în timpul procesului de imagere (sau ulterior prin sudo raspi-config).

Conectarea la Raspberry Pi:

Conectează-te prin SSH de pe computerul tău:
ssh pi@<adresa_ip_a_raspberry_pi>

Instalarea Dependențelor Python pe RPi:

Actualizează lista de pachete și instalează pip pentru Python 3:
sudo apt update
sudo apt upgrade
sudo apt install python3-pip

Instalează bibliotecile Python necesare pentru controlul GPIO, cameră, OCR etc.:

pip3 install RPi.GPIO picamera2 Pillow opencv-python pytesseract paramiko
sudo apt install tesseract-ocr

Activarea Interfețelor Hardware:
sudo raspi-config

Navighează la Interface Options și activează:
Camera (pentru modulul camerei Pi)
I2C (pentru ecranul LCD)
SSH (dacă nu l-ai activat deja)

Clonarea Repository-ului cu Scripturile: git clone [adresa_repository]/smart_parking_pi.git SmartParkingPi

Configurarea Cheilor SSH (pentru comunicarea Django-RPi):
Generează o pereche de chei SSH pe Raspberry Pi: ssh-keygen -t rsa -b 4096

Copiază conținutul cheii publice (~/.ssh/id_rsa.pub) de pe Raspberry Pi pe serverul unde rulează backend-ul Django, în fișierul ~/.ssh/authorized_keys al utilizatorului sub care rulează procesul Django. Acest lucru permite backend-ului să execute comenzi pe RPi fără parolă.



Pași de Instalare și Lansare a Aplicației
Lansarea Backend-ului (Django Server)
Navighează în Directorul Backend:  cd /path/to/your/smart_parking_backend
Lansează Serverul de Dezvoltare:  python manage.py runserver 0.0.0.0:8000
Lansarea Aplicației Mobile (Flutter): 
Navighează în Directorul Aplicației Flutter: cd /path/to/your/smart_parking_app
Asigură-te că un Emulator/Dispozitiv este Conectat:
Pornește un emulator Android din Android Studio sau conectează un telefon fizic
Verifică dispozitivele conectate: flutter devices
Lansează Aplicația: flutter run
Această comandă va compila și va instala aplicația pe dispozitivul/emulatorul conectat și o va lansa.


 Lansarea Scripturilor pe Raspberry Pi
Scripturile de pe Raspberry Pi rulează în două moduri principale: unele pornesc automat la boot sau sunt menținute active în fundal, în timp ce altele sunt declanșate la cerere de către backend-ul Django prin SSH.
Lansarea Scripturilor de Barieră și Detecție (Triggerate de Backend):
Scripturile precum main_pi_script.py, main_pi_script_exit.py, up.py, down.py și update_spots.py nu se lansează manual, ci sunt apelate automat prin SSH de către backend-ul Django (views.py) atunci când evenimente specifice au loc (ex: detectarea unei mașini la intrare, cerere de plată finalizată). Backend-ul folosește biblioteca paramiko pentru a executa aceste scripturi pe Raspberry Pi.
