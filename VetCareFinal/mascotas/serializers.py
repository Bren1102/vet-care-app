from rest_framework import serializers
from .models import Mascota, Veterinaria, Turno

class MascotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mascota
        fields = '__all__'
        read_only_fields = ('dueño',)

class VeterinariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Veterinaria
        fields = '__all__'

class TurnoSerializer(serializers.ModelSerializer):
    # Sumamos estos campos detallados para que el GET devuelva los objetos completos
    mascota_detalle = MascotaSerializer(source='mascota', read_only=True)
    veterinaria_detalle = VeterinariaSerializer(source='veterinaria', read_only=True)

    class Meta:
        model = Turno
        fields = [
            'id', 
            'mascota', 
            'veterinaria', 
            'fecha_hora', 
            'motivo', 
            'mascota_detalle', 
            'veterinaria_detalle'
        ]