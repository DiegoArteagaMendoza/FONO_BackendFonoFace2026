from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from PmCliente.models import PmCliente


class PmClienteRegistroSerializer(serializers.ModelSerializer):
    """
    Registro del paciente. La contraseña entra como campo de solo escritura y
    nunca vuelve en la respuesta.
    """
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

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
            'password',
        ]
        read_only_fields = ['id_cliente']

    def validate_rut_cliente(self, value):
        """
        Normaliza el RUT: sin puntos ni espacios y con la K en mayúscula, que es
        la convención chilena. Guardarlo siempre igual es lo que permite después
        iniciar sesión con el RUT sin importar cómo lo escriba la persona.
        """
        return value.replace('.', '').replace(' ', '').strip().upper()

    def validate_email_cliente(self, value):
        return value.strip().lower()

    def create(self, validated_data):
        try:
            return PmCliente.objects.crear_cliente(
                nombres=validated_data['nombres_cliente'],
                apellidos=validated_data['apellidos_clientes'],
                rut=validated_data['rut_cliente'],
                fecha_nacimiento=validated_data['fecha_nacimiento_cliente'],
                email=validated_data['email_cliente'],
                telefono=validated_data['telefono_cliente'],
                password=validated_data['password'],
            )
        except DjangoValidationError as error:
            detalle = error.message_dict if hasattr(error, 'message_dict') else error.messages
            raise serializers.ValidationError(detalle)


class PmClienteSerializer(serializers.ModelSerializer):
    """
    Vista del paciente para su propio perfil y para el profesional que lo atiende.
    Nunca expone password_cliente.
    """
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
        read_only_fields = ['id_cliente', 'rut_cliente', 'fecha_creacion', 'fecha_actualizacion', 'estado']

    def validate_email_cliente(self, value):
        return value.strip().lower()


class PmClienteLoginSerializer(serializers.Serializer):
    identificador = serializers.CharField(help_text='Correo o RUT del paciente')
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class PmClienteCambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nueva = serializers.CharField(write_only=True, min_length=8)
