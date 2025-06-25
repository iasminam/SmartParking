from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import DriverSerializer, UserSerializer
from .models import Driver
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
import logging
import stripe
import paramiko #import pentru SSH
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt #pentru confirm_payment
import time
from datetime import datetime
import json #pentru create_payment_intent și confirm_payment

logger = logging.getLogger(__name__)

#configurare SSH pentru Raspberry Pi
RASPBERRY_PI_HOST = '172.20.10.2'
RASPBERRY_PI_USER = 'pi'
RASPBERRY_KEY_PATH = 'C:/Users/iasmi/.ssh/id_rsa' # Calea către cheia privată SSH de pe serverul Django.

# Căile absolute ale scripturilor de pe Raspberry Pi
MAIN_PI_SCRIPT = '/usr/bin/python3 /home/pi/Desktop/SmartParking/main_pi_script.py'
MAIN_PI_SCRIPT_EXIT = '/usr/bin/python3 /home/pi/Desktop/SmartParking/main_pi_script_exit.py'
UPDATE_SPOTS_SCRIPT = '/usr/bin/python3 /home/pi/Desktop/SmartParking/update_spots.py'
BARRIER_UP_SCRIPT = '/usr/bin/python3 /home/pi/Desktop/SmartParking/output/up.py'
BARRIER_DOWN_SCRIPT = '/usr/bin/python3 /home/pi/Desktop/SmartParking/output/down.py'

AUTHORIZED_PLATES = ['TM11DDD']

stripe.api_key = settings.STRIPE_SECRET_KEY

#Declanșează detecția mașinii pe Raspberry Pi prin SSH.Verifică plăcuța și controlează bariera și locurile libere.
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def trigger_car_detection(request):
    driver = get_object_or_404(Driver, user=request.user)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        private_key = paramiko.RSAKey.from_private_key_file(RASPBERRY_KEY_PATH)
        client.connect(hostname=RASPBERRY_PI_HOST, username=RASPBERRY_PI_USER, pkey=private_key)

        command = f'sudo {MAIN_PI_SCRIPT}'
        
        stdin, stdout, stderr = client.exec_command(command)
        
        pi_output = stdout.read().decode().strip()
        pi_errors = stderr.read().decode().strip()

        logger.info(f"RPi script output: {pi_output}")
        if pi_errors:
            logger.error(f"RPi script errors: {pi_errors}", exc_info=True)

        license_plate = pi_output if pi_output and pi_output != "PLACA_NEDETECTATA" else None

        response_data = {}
        status_code = status.HTTP_200_OK

        if license_plate:
            if (driver.car_number_plate and driver.car_number_plate.upper() == license_plate.upper()) or \
               (license_plate.upper() in AUTHORIZED_PLATES):
                
                # Placă autorizată: Deschide bariera și scade locurile
                open_barrier_and_update_spots_command = (
                    f'sudo {BARRIER_UP_SCRIPT} && sleep 5 && sudo {BARRIER_DOWN_SCRIPT} && '
                    f'sudo {UPDATE_SPOTS_SCRIPT} enter'
                )
                
                stdin_cmd, stdout_cmd, stderr_cmd = client.exec_command(open_barrier_and_update_spots_command)
                logger.info(f"Barrier and spots update script output: {stdout_cmd.read().decode().strip()}")
                error_output = stderr_cmd.read().decode().strip()
                if error_output:
                    logger.error(f"Barrier and spots update script errors: {error_output}", exc_info=True)
                
                # Actualizează data de sosire a driverului
                if not driver.date_of_arrival:
                    driver.date_of_arrival = timezone.now()
                    driver.save()

                response_data = {
                    'status': 'success',
                    'message': 'Placa autorizata. Bariera deschisa si locuri actualizate.',
                    'detected_plate': license_plate
                }
                status_code = status.HTTP_200_OK

            else:
                # Placă neautorizată: Asigură bariera închisă
                close_barrier_command = f'sudo {BARRIER_DOWN_SCRIPT}'
                stdin_down, stdout_down, stderr_down = client.exec_command(close_barrier_command)
                logger.info(f"Barrier DOWN script output: {stdout_down.read().decode().strip()}")
                error_output = stderr_down.read().decode().strip()
                if error_output:
                    logger.error(f"Barrier DOWN script errors: {error_output}", exc_info=True)

                response_data = {
                    'status': 'unauthorized',
                    'message': 'Placa detectata, dar neautorizata.',
                    'detected_plate': license_plate
                }
                status_code = status.HTTP_403_FORBIDDEN

        else:
            # Placă nedetectată: Asigură bariera închisă
            close_barrier_command = f'sudo {BARRIER_DOWN_SCRIPT}'
            stdin_down, stdout_down, stderr_down = client.exec_command(close_barrier_command)
            logger.info(f"Barrier DOWN script output: {stdout_down.read().decode().strip()}")
            error_output = stderr_down.read().decode().strip()
            if error_output:
                logger.error(f"Barrier DOWN script errors: {error_output}", exc_info=True)

            response_data = {
                'status': 'not_detected',
                'message': 'Placa nedetectata de sistem.',
                'detected_plate': None
            }
            status_code = status.HTTP_400_BAD_REQUEST

        return Response(response_data, status=status_code)

    except paramiko.AuthenticationException:
        logger.error("SSH Authentication failed. Check username and key path.", exc_info=True)
        return Response({'status': 'error', 'message': 'Eroare de autentificare SSH.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except paramiko.SSHException as e:
        logger.error(f"Could not establish SSH connection: {e}", exc_info=True)
        return Response({'status': 'error', 'message': f'Eroare la conectarea SSH: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Internal server error during RPi interaction: {e}", exc_info=True)
        return Response({'status': 'error', 'message': f'Eroare interna a serverului: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        if client:
            client.close()

# Simulează intrarea unei mașini în parcare. Acest endpoint este pentru testare/demonstrație.
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def simulate_parking(request):
    try:
        driver = Driver.objects.get(user=request.user)
        if driver.date_of_arrival:
            return Response({"detail": "Soferul este deja parcat."}, status=status.HTTP_400_BAD_REQUEST)

        driver.date_of_arrival = timezone.now() 
        driver.save()
        return Response({"detail": "Parcare simulata cu succes. Data sosirii inregistrata."}, status=status.HTTP_200_OK)

    except Driver.DoesNotExist:
        return Response({"detail": "Soferul nu a fost gasit."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Eroare in simulate_parking: {str(e)}", exc_info=True)
        return Response({"detail": f"Eroare interna a serverului: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Acesta este un endpoint de verificare a stării barierei. În implementarea curentă, bariera este controlată direct de serverul Django după detecție/autorizare.
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_barrier_open_status(request):
    return Response({"open_barrier": False, "message": "Starea barierei este controlata direct de serverul Django dupa detectie."}, status=status.HTTP_200_OK)

# Acesta este un endpoint de simulat detecția mașinii. Nu mai este folosit direct de Flutter pentru detecție.
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def simulate_car_detection(request):
    return Response({"detail": "Acest endpoint nu mai este folosit pentru detectie directa. Foloseste /api/drivers/trigger_car_detection/."}, status=status.HTTP_410_GONE)

# Calculează costul parcării și inițiază un Payment Intent. 
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def simulate_departure(request):
    try:
        driver = get_object_or_404(Driver, user=request.user)
        if not driver.date_of_arrival:
            return Response({"detail": "Soferul nu este parcat. Nu se poate calcula costul de plecare."}, status=status.HTTP_400_BAD_REQUEST)

        arrival_time = driver.date_of_arrival
        departure_time = timezone.now() 
        duration = departure_time - arrival_time
        seconds = duration.total_seconds()
   
        if seconds < 0:
            seconds = 0

        FREE_PARKING_THRESHOLD_SECONDS = 10 # timpul de parcare gratuit (10 secunde)
        COST_PER_SECOND = 0.1 
        MINIMUM_STRIPE_CHARGE_RON = 2.00 # 2 RON = 200 bani
        
        total_cost_ron = 0.00
        amount_in_bani = 0
        payment_status_to_save = 'pending' # valoare inițială
        payment_intent_id_to_save = None
        client_secret_to_return = None

        if seconds <= FREE_PARKING_THRESHOLD_SECONDS:
            logger.info(f"Parcare gratuita pentru soferul {driver.user.username} (durata: {seconds:.2f} secunde <= {FREE_PARKING_THRESHOLD_SECONDS} secunde).")
            total_cost_ron = 0.00
            payment_status_to_save = 'free'
        else:
            total_cost_ron = seconds * COST_PER_SECOND
            
            if total_cost_ron < MINIMUM_STRIPE_CHARGE_RON:
                original_amount_ron = total_cost_ron
                total_cost_ron = MINIMUM_STRIPE_CHARGE_RON
                logger.info(f"Calculated amount {original_amount_ron:.2f} RON is below Stripe minimum. Setting charge to {MINIMUM_STRIPE_CHARGE_RON:.2f} RON.")

            amount_in_bani = int(total_cost_ron * 100)

            #Stripe.
            logger.info(f"Attempting to create Stripe PaymentIntent for driver_id={driver.user.id}, amount={amount_in_bani}, currency='ron'")
            
            intent = stripe.PaymentIntent.create(
                amount=amount_in_bani,
                currency='ron',
                automatic_payment_methods={"enabled": True}, 
                metadata={'driver_id': driver.user.id}, 
            )
            
            logger.info(f"Stripe PaymentIntent created: {intent.id}")
            payment_status_to_save = 'pending_payment' # Setăm la pending_payment dacă e nevoie de plată
            payment_intent_id_to_save = intent.id
            client_secret_to_return = intent.client_secret

        # Salvăm starea driverului indiferent dacă e gratuit sau cu plată
        driver.payment_status = payment_status_to_save
        driver.payment_intent_id = payment_intent_id_to_save
        driver.paid_amount = total_cost_ron
        driver.save()

        return Response({
            "detail": "Proces de plecare initiat.",
            "clientSecret": client_secret_to_return, # Va fi null pentru parcare gratuita
            "total_cost": total_cost_ron,
            "payment_status": driver.payment_status, # Va fi 'free' sau 'pending_payment'
            "payment_intent_id": payment_intent_id_to_save,
        }, status=status.HTTP_200_OK)

    except stripe.error.AuthenticationError as e:
        logger.error(f"Stripe Authentication Error (API Key likely invalid): {e.user_message if hasattr(e, 'user_message') else str(e)}", exc_info=True)
        return Response({"detail": f"Eroare Stripe de Autentificare: Verificati cheia API. Detalii: {e.user_message if hasattr(e, 'user_message') else str(e)}"}, status=status.HTTP_401_UNAUTHORIZED)
    except stripe.error.StripeError as e:
        logger.error(f"Generic Stripe API Error in simulate_departure: {e.user_message if hasattr(e, 'user_message') else str(e)}", exc_info=True)
        # Nu modificăm payment_status aici, deoarece e o eroare la creare, nu la plată efectivă
        return Response({"detail": f"Eroare Stripe: {e.user_message if hasattr(e, 'user_message') else str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Driver.DoesNotExist:
        return Response({"detail": "Soferul nu a fost gasit."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Eroare interna a serverului in simulate_departure: {str(e)}", exc_info=True)
        return Response({"detail": f"Eroare interna a serverului: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Endpoint apelat de frontend după o plată reușită cu Stripe Payment Sheet.  Actualizează statusul plății driverului la 'paid'.
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated]) # Driverul trebuie să fie autentificat
@csrf_exempt
def confirm_payment(request):
    try:
        driver = get_object_or_404(Driver, user=request.user)
        payment_intent_id = request.data.get('paymentIntentId')   # Obține PaymentIntent ID-ul din request body (trimis de Flutter)

        if not payment_intent_id:
            logger.warning(f"confirm_payment called by {driver.user.username} without paymentIntentId.")
            return Response({"detail": "Payment Intent ID lipsește."}, status=status.HTTP_400_BAD_REQUEST)

        # Verifică PaymentIntent-ul direct la Stripe pentru siguranță
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            # Verifică dacă PaymentIntent-ul aparține driverului curent (pentru siguranță suplimentară)
            if intent.metadata.get('driver_id') != str(driver.user.id):
                logger.warning(f"Attempted payment confirmation for mismatched driver. Request driver: {driver.user.id}, PaymentIntent driver: {intent.metadata.get('driver_id')}")
                return Response({"detail": "Payment Intent ID nu corespunde cu utilizatorul curent."}, status=status.HTTP_403_FORBIDDEN)

            if intent.status == 'succeeded':
                # Asigură că driverul curent este cel pentru care a fost creat PaymentIntent-ul și că nu a fost deja marcat ca plătit sau gratuit.
                if driver.payment_status != 'paid' and driver.payment_intent_id == payment_intent_id:
                    driver.payment_status = 'paid'
                    driver.save()
                    logger.info(f"Driver {driver.user.username} (ID: {driver.user.id}) payment status updated to 'paid' via confirm_payment endpoint for PaymentIntent {payment_intent_id}.")
                    return Response({"detail": "Plata confirmata cu succes.", "payment_status": driver.payment_status}, status=status.HTTP_200_OK)
                elif driver.payment_status == 'paid':
                    logger.info(f"Driver {driver.user.username} payment for PaymentIntent {payment_intent_id} already marked as 'paid'. No action needed.")
                    return Response({"detail": "Plata a fost deja confirmata anterior.", "payment_status": driver.payment_status}, status=status.HTTP_200_OK)
                else:
                    logger.warning(f"PaymentIntent {payment_intent_id} status is 'succeeded' but driver's current payment_intent_id is '{driver.payment_intent_id}' or payment_status is '{driver.payment_status}'.")
                    return Response({"detail": "PaymentIntent ID valid, dar statusul driverului nu permite actualizarea sau PaymentIntent-ul nu corespunde intentiei curente."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                logger.warning(f"PaymentIntent {payment_intent_id} status is '{intent.status}'. Expected 'succeeded'. Payment status remains {driver.payment_status}.")
                return Response({"detail": f"Statusul platii nu este 'succeeded'. Status actual: {intent.status}"}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving PaymentIntent {payment_intent_id} from Stripe: {e}", exc_info=True)
            return Response({"detail": f"Eroare la verificarea platii cu Stripe: {e.user_message if hasattr(e, 'user_message') else str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Driver.DoesNotExist:
        return Response({"detail": "Soferul nu a fost gasit."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Internal server error in confirm_payment: {e}", exc_info=True)
        return Response({"detail": f"Eroare interna a serverului: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""
    Gestionează procesul de ieșire din parcare:
    1. Verifică dacă driverul este parcat (are date_of_arrival).
    2. Declanșează detecția plăcuței la barieră (Raspberry Pi - script dedicat ieșirii).
    3. Verifică plăcuța detectată cu cea a driverului.
    4. Verifică statusul plății driverului (inclusiv 'free').
    5. Actualizează numărul de locuri libere.
    6. Deschide/închide bariera corespunzător.
    7. Resetează starea driverului în baza de date.
"""
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_departure(request):
    driver = get_object_or_404(Driver, user=request.user)

    if not driver.date_of_arrival:
        return Response({"detail": "Nu esti parcat. Nu poți iniția plecarea."}, status=status.HTTP_400_BAD_REQUEST)

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        private_key = paramiko.RSAKey.from_private_key_file(RASPBERRY_KEY_PATH)
        client.connect(hostname=RASPBERRY_PI_HOST, username=RASPBERRY_PI_USER, pkey=private_key)

        command_get_plate = f'sudo {MAIN_PI_SCRIPT_EXIT}'
        
        logger.info(f"Triggering plate detection on RPi for departure using: {command_get_plate}")
        stdin, stdout, stderr = client.exec_command(command_get_plate)
        
        pi_output = stdout.read().decode().strip()
        pi_errors = stderr.read().decode().strip()

        logger.info(f"RPi departure script output: '{pi_output}'")
        if pi_errors:
            logger.error(f"RPi departure script errors: {pi_errors}", exc_info=True)
        
        detected_plate = pi_output if pi_output and pi_output != "PLACA_NEDETECTATA" else None

        response_data = {}
        status_code = status.HTTP_200_OK
        
        open_barrier = False

        if detected_plate:
            if driver.car_number_plate and driver.car_number_plate.upper() == detected_plate.upper():
                # Reîncarcă driverul înainte de verificare pentru a fi sigur că este cel mai recent status.
                driver.refresh_from_db() 
                logger.info(f"Driver {driver.user.username} payment_status after refresh: {driver.payment_status}")

                if driver.payment_status == 'paid' or driver.payment_status == 'free': 
                    open_barrier = True
                    response_data = {
                        'message': 'Placa detectată si plata confirmata/parcare gratuita. Bariera se deschide.', 
                        'detected_plate': detected_plate,
                    }
                    status_code = status.HTTP_200_OK

                else:
                    logger.warning(f"Departure attempt by {driver.user.username}: Plate {detected_plate} matched, but payment status is '{driver.payment_status}'.")
                    response_data = {
                        'detail': 'Placa detectata, dar plata nu a fost confirmata. Va rugam finalizati plata.',
                        'detected_plate': detected_plate
                    }
                    # Păstrăm statusul 402 pentru a indica necesitatea plății
                    status_code = status.HTTP_402_PAYMENT_REQUIRED 

            else:
                logger.warning(f"Departure attempt by {driver.user.username}: Detected plate '{detected_plate}' does not match registered plate '{driver.car_number_plate}'.")
                response_data = {
                    'detail': f'Placa detectata ({detected_plate}) nu corespunde cu cea inregistrata ({driver.car_number_plate}).',
                    'detected_plate': detected_plate
                }
                status_code = status.HTTP_403_FORBIDDEN

        else:
            logger.warning(f"Departure attempt by {driver.user.username}: No plate detected from RPi exit script.")
            response_data = {
                'detail': 'Placa nu a putut fi detectata. Va rugam pozitionati masina corect.',
                'detected_plate': None
            }
            status_code = status.HTTP_400_BAD_REQUEST

        if open_barrier:
            try:
                now_aware = timezone.now()
                
                arrival_time = driver.date_of_arrival
                duration = now_aware - arrival_time
                duration_minutes = int(duration.total_seconds() / 60)

                driver.date_of_arrival = None
                driver.date_of_departure = now_aware
                driver.paid_amount = 0.00
                driver.payment_intent_id = None
                driver.payment_status = 'pending' # Resetăm la 'pending' pentru următoarea parcare
                driver.save()

                logger.info(f"Driver {driver.user.username} departed. Duration: {duration_minutes} mins.")

                update_spots_command = f'sudo {UPDATE_SPOTS_SCRIPT} exit'
                stdin_spots, stdout_spots, stderr_spots = client.exec_command(update_spots_command)
                spots_update_output = stdout_spots.read().decode().strip()
                spots_update_errors = stderr_spots.read().decode().strip()
                logger.info(f"Update spots script (departure) output: {spots_update_output}")
                if spots_update_errors:
                    logger.error(f"Update spots script (departure) errors: {spots_update_errors}", exc_info=True)

                open_close_barrier_command = f'sudo {BARRIER_UP_SCRIPT} && sleep 5 && sudo {BARRIER_DOWN_SCRIPT}'
                stdin_ocb, stdout_ocb, stderr_ocb = client.exec_command(open_close_barrier_command)
                barrier_action_output = stdout_ocb.read().decode().strip()
                barrier_action_errors = stderr_ocb.read().decode().strip()
                logger.info(f"Barrier UP/DOWN script (departure) output: {barrier_action_output}")
                if barrier_action_errors:
                    logger.error(f"Barrier UP/DOWN script (departure) errors: {barrier_action_errors}", exc_info=True)

                response_data['message'] = "Plecarea a fost inregistrata cu succes. Bariera s-a deschis. Drum bun!"
                response_data['entry_time'] = arrival_time.isoformat()
                response_data['exit_time'] = now_aware.isoformat()
                response_data['duration_minutes'] = duration_minutes

            except paramiko.SSHException as e:
                logger.error(f"Eroare SSH la controlul barierei sau actualizarea locurilor: {e}", exc_info=True)
                return Response({'detail': f'Eroare la controlul barierei sau actualizarea locurilor: {e}. '
                                            'Plecarea a fost înregistrată în baza de date, dar a apărut o problemă cu RPi.'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                logger.error(f"Eroare neașteptată la actualizarea DB/RPi post-detecție: {e}", exc_info=True)
                return Response({'detail': f'Eroare internă la procesarea plecării: {e}. '
                                            'Verificați manual starea barierei și a locurilor de parcare.'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            try:
                # Bariera se închide doar dacă nu s-a deschis
                close_barrier_command = f'sudo {BARRIER_DOWN_SCRIPT}'
                stdin_down, stdout_down, stderr_down = client.exec_command(close_barrier_command)
                barrier_down_output = stdout_down.read().decode().strip()
                barrier_down_errors = stderr_down.read().decode().strip()
                logger.info(f"Barrier DOWN script (departure - conditions not met) output: {barrier_down_output}")
                if barrier_down_errors:
                    logger.error(f"Barrier DOWN script (departure - conditions not met) errors: {barrier_down_errors}", exc_info=True)
            except paramiko.SSHException as e:
                logger.error(f"Eroare SSH la închiderea barierei (condiții neîndeplinite): {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Eroare neașteptată la închiderea barierei (condiții neîndeplinite): {e}", exc_info=True)
            
        return Response(response_data, status=status_code)

    except paramiko.AuthenticationException:
        logger.error("SSH Authentication failed during departure verification. Check username and key path.", exc_info=True)
        return Response({'detail': 'Eroare de autentificare SSH. Verificați credențialele Raspberry Pi.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except paramiko.SSHException as e:
        logger.error(f"Could not establish SSH connection during departure verification: {e}", exc_info=True)
        return Response({'detail': f'Eroare la conectarea SSH cu Raspberry Pi: {e}. Asigurați-vă că RPi este online și accesibil.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Internal server error during RPi departure interaction: {e}", exc_info=True)
        return Response({'detail': f'Eroare internă a serverului la verificarea plecarii: {e}.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        if client:
            client.close()

class DriverPageView(generics.RetrieveUpdateAPIView):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    lookup_field = 'user__username'

class DriverRegistrationView(generics.CreateAPIView):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = (permissions.AllowAny,)

    def perform_create(self, serializer):
        # serializer.save() va apela metoda `create` din DriverSerializer care se va ocupa de crearea User-ului și a Driver-ului.
        instance = serializer.save() 
        username = self.request.data.get('username')
        password = self.request.data.get('password') # Extragem parola clară din request.data

        if not username or not password:
            logger.error("Username or password missing from request data for authentication.")
            self.response = Response({'error': 'Username sau parola lipsesc pentru autentificare.'}, status=status.HTTP_400_BAD_REQUEST)
            return

        authenticated_user = authenticate(username=username, password=password)

        if authenticated_user:
            refresh = RefreshToken.for_user(authenticated_user)
            response_data = {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'driver_name': instance.driver_name,
                'username': authenticated_user.username,
                'api_key': instance.api_key
            }
            self.response = Response(response_data, status=status.HTTP_201_CREATED)
            logger.info(f"Driver {authenticated_user.username} registered and authenticated successfully.")
        else:
            logger.error(f"Failed to authenticate user {username} after registration (likely wrong password or inactive user).")
            self.response = Response({'error': 'Autentificare eșuată după înregistrare. Verificați credențialele sau statusul contului.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Metoda post este suprascrisă pentru a returna `self.response` setat în `perform_create`.
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        # Verificăm dacă perform_create a setat `self.response`.
        if hasattr(self, 'response'):
            return self.response
        else:
            return response 


class UserLoginView(generics.GenericAPIView):
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            try:
                driver = Driver.objects.get(user=user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'driver_name': driver.driver_name,
                    'username': user.username,
                    'api_key': driver.api_key
                })
            except Driver.DoesNotExist:
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'username': user.username,
                    'driver_name': None,
                    'api_key': None
                }, status=status.HTTP_200_OK)
        return Response({'error': 'Credentiale invalide'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def create_payment_intent(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = data['amount']
            currency = data['currency']
            
            if currency == 'ron' and amount < 200: # 200 bani = 2 RON (minim Stripe)
                return Response({'error': 'Suma trebuie sa fie de cel putin 200 bani (2 RON)'}, status=status.HTTP_400_BAD_REQUEST)
            
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                automatic_payment_methods={
                    'enabled': True,
                },
            )
            return Response({'clientSecret': intent['client_secret']}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Eroare Stripe: {str(e)}', exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({'error': 'Metoda de cerere invalida'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)