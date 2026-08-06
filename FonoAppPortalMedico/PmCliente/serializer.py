from rest_framework import serializers
from PmCliente.models import PmCliente


class PmClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PmCliente
        fields = [
            'id_cliente',
            'nombres_cliente',
            'apellidos_clientes',
            'rut_cliente',
            'fecha_nacimiento_cliente',
            'email_cliente',
            'telefono_cliente',
            'fecha_creacion',
            'fecha_actualizacion',
            'estado',
        ]
        # El frontend no debe enviar ni modificar estos campos
        read_only_fields = ['id_cliente', 'fecha_creacion', 'fecha_actualizacion', 'estado']

    def validate_rut_cliente(self, value):
        """Normaliza el RUT (sin puntos, en minúscula) antes de guardarlo."""
        return value.replace('.', '').replace(' ', '').strip().lower()

    def validate_email_cliente(self, value):
        return value.strip().lower()
