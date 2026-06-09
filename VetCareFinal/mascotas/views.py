from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from django.contrib.sessions.models import Session
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.conf import settings
from .models import Mascota, Veterinaria, Turno, Perfil
from .serializers import MascotaSerializer, VeterinariaSerializer, TurnoSerializer

class MascotaViewSet(viewsets.ModelViewSet):
    """ViewSet que limita las mascotas al usuario autenticado."""
    queryset = Mascota.objects.none()
    serializer_class = MascotaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated:
            return Mascota.objects.filter(dueño=user)
        return Mascota.objects.none()

    def perform_create(self, serializer):
        # Asignar el usuario autenticado como dueño al crear mascota
        serializer.save(dueño=self.request.user)

class VeterinariaViewSet(viewsets.ModelViewSet):
    queryset = Veterinaria.objects.all()
    serializer_class = VeterinariaSerializer

class TurnoViewSet(viewsets.ModelViewSet):
    queryset = Turno.objects.all()
    serializer_class = TurnoSerializer

# --- VISTA PARA REGISTRAR USUARIOS DESDE EL FRONTEND ---

@api_view(['POST'])
@permission_classes([AllowAny])  # Permite que usuarios no logueados accedan a registrarse
def registrar_usuario(request):
    data = request.data
    
    # Extraemos las variables que configuramos en el formulario de React
    fullname = data.get('fullName')
    email = data.get('email')
    telefono = data.get('phone')
    password = data.get('password')
    
    # Validaciones rápidas de seguridad en el servidor
    if not email or not password or not fullname:
        return Response({'message': 'Faltan campos obligatorios.'}, status=status.HTTP_400_BAD_REQUEST)
        
    if User.objects.filter(email=email).exists():
        return Response({'message': 'Este correo electrónico ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        # 1. Creamos el usuario base de Django (usamos el mail como username obligatorio)
        user = User.objects.create(
            username=email,
            email=email,
            first_name=fullname
        )
        
        # 2. Encriptamos la contraseña de forma segura (Hasheo automático)
        user.set_password(password)
        user.save()
        
        # 3. Guardamos el teléfono en el Perfil asociado que agregamos en el models.py
        Perfil.objects.create(user=user, telefono=telefono)
        
        return Response({'message': 'Usuario registrado con éxito.'}, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'message': f'Error al registrar el usuario: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_usuario(request):
    data = request.data
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return Response({'message': 'Email y contraseña son obligatorios.'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=email, password=password)
    if user is None:
        return Response({'message': 'Email o contraseña incorrectos.'}, status=status.HTTP_401_UNAUTHORIZED)

    login(request, user)

    return Response(
        {
            'message': 'Inicio de sesión correcto.',
            'first_name': user.first_name,
            'email': user.email,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_usuario(request):
    """Cerrar sesión del usuario autenticado.

    Simplificamos la lógica: usar `logout(request)` y `response.delete_cookie`.
    El frontend debe enviar `X-CSRFToken` y `credentials: 'include'`.
    """
    try:
        logout(request)
    except Exception:
        pass

    response = JsonResponse({'message': 'Sesión cerrada correctamente.'}, status=200)

    # Borrar la cookie de sesión; evitamos forzar domain explícito para no romper en dev
    cookie_name = settings.SESSION_COOKIE_NAME
    cookie_path = getattr(settings, 'SESSION_COOKIE_PATH', '/') or '/'
    try:
        response.delete_cookie(cookie_name, path=cookie_path)
    except Exception:
        # nada crítico si falla
        pass

    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """Devuelve los datos del usuario autenticado y su perfil."""
    user = request.user
    try:
        perfil = Perfil.objects.filter(user=user).first()
        telefono = perfil.telefono if perfil else ''
    except Exception:
        telefono = ''

    data = {
        'first_name': user.first_name,
        'email': user.email,
        'phone': telefono,
    }

    return Response(data, status=status.HTTP_200_OK)

# --- VISTA PARA MODIFICAR EL PERFIL DE USUARIO (ACTUALIZACIÓN) ---

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def modificar_perfil(request):
    """Permite al usuario autenticado modificar sus datos personales y su teléfono."""
    user = request.user
    data = request.data

    fullname = data.get('fullName')
    email = data.get('email')
    telefono = data.get('phone')

    try:
        # 1. Actualizamos datos en el modelo User base de Django
        if fullname:
            user.first_name = fullname
        
        if email:
            # Validamos que el mail nuevo no lo esté usando otra persona
            if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                return Response({'message': 'Este correo electrónico ya está en uso por otro usuario.'}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email
            user.username = email  # Mantenemos el username sincronizado porque usan el mail
        user.save()

        # 2. Actualizamos o creamos el teléfono en el Perfil asociado que armó Aldana
        perfil, created = Perfil.objects.get_or_create(user=user)
        if telefono is not None:
            perfil.telefono = telefono
            perfil.save()

        return Response({'message': 'Perfil actualizado correctamente.'}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'message': f'Error al actualizar el perfil: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)