from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from Security.archivos import url_absoluta
from PmMedico.models import (
    PM_Profesional,
    PM_Acreditacion,
    PM_Documento_Respaldo,
    PM_Especialidad,
    PM_Profesional_especialidad,
)


# =========================================================
# 1. ESPECIALIDAD (tabla de dominio)
# =========================================================
class PM_EspecialidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PM_Especialidad
        fields = ['id_especialidad', 'nombre_especialidad_profesional', 'especialidad_requiere_certificado']
        read_only_fields = ['id_especialidad']


# =========================================================
# 2. ESPECIALIDADES ASIGNADAS A UN PROFESIONAL (M:N)
# =========================================================
class PM_Profesional_especialidadSerializer(serializers.ModelSerializer):
    # Salida anidada de solo lectura con el detalle de la especialidad
    especialidad = PM_EspecialidadSerializer(source='id_especialidad', read_only=True)
    # Entrada: el frontend solo manda el id de la especialidad a asignar
    id_especialidad = serializers.PrimaryKeyRelatedField(
        queryset=PM_Especialidad.objects.all(), write_only=True
    )

    class Meta:
        model = PM_Profesional_especialidad
        fields = ['id_especialidad', 'especialidad', 'fecha_asignacion']
        read_only_fields = ['fecha_asignacion']

    def create(self, validated_data):
        profesional = self.context['request'].user
        especialidad = validated_data['id_especialidad']
        try:
            relacion, _creada = PM_Profesional_especialidad.objects.asignar(profesional, especialidad)
        except DjangoValidationError as error:
            raise serializers.ValidationError({'id_especialidad': error.messages})
        return relacion


# =========================================================
# 3. DOCUMENTO DE RESPALDO
# =========================================================
class PM_Documento_RespaldoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PM_Documento_Respaldo
        fields = [
            'id_documento', 'id_profesional', 'tipo_documeto_profesional',
            'url_documento_profesional', 'fecha_subida_documento_profesional',
            'documento_profesional_valido',
        ]
        read_only_fields = [
            'id_documento', 'id_profesional', 'fecha_subida_documento_profesional',
            'documento_profesional_valido',
        ]

    def to_representation(self, instance):
        """
        El documento es un CloudinaryField: serializado tal cual entrega el
        public_id, no una URL. Se reemplaza por la URL https real para que el
        administrador pueda abrir el PDF desde el panel.
        """
        datos = super().to_representation(instance)
        datos['url_documento_profesional'] = url_absoluta(instance.url_documento_profesional)
        return datos

    def create(self, validated_data):
        profesional = self.context['request'].user
        return PM_Documento_Respaldo.objects.subir_documento(
            profesional=profesional,
            tipo_documento=validated_data['tipo_documeto_profesional'],
            archivo=validated_data['url_documento_profesional'],
        )


# =========================================================
# 4. ACREDITACIÓN
# =========================================================
class PM_AcreditacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PM_Acreditacion
        fields = [
            'id_acreditacion', 'id_profesional', 'estado_verificacion_profesional',
            'fecha_solicitud_profesional', 'fecha_resolucion_profesional',
            'id_administrador_resolutor',
        ]
        read_only_fields = fields  # Se gestiona íntegramente vía queryset (crear_profesional / resolver)


class PM_ResolverAcreditacionSerializer(serializers.Serializer):
    """Solo usado para validar el body del endpoint de aprobar/rechazar."""
    estado_verificacion_profesional = serializers.ChoiceField(choices=['APROBADO', 'RECHAZADO'])


# =========================================================
# 5. PROFESIONAL
# =========================================================
class PM_ProfesionalRegistroSerializer(serializers.ModelSerializer):
    """
    Registro inicial ágil: solo pide lo indispensable. numero_registro_salud
    queda opcional (se exigirá recién al aprobar la acreditación).
    """
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})

    class Meta:
        model = PM_Profesional
        fields = [
            'id_profesional', 'nombres_profesional', 'apellidos_profesional', 'rut_profesional',
            'numero_registro_salud_profesional', 'email_profesional', 'telefono_profesional', 'password',
        ]
        read_only_fields = ['id_profesional']
        extra_kwargs = {
            'numero_registro_salud_profesional': {'required': False},
        }

    def create(self, validated_data):
        try:
            return PM_Profesional.objects.crear_profesional(
                nombres=validated_data['nombres_profesional'],
                apellidos=validated_data['apellidos_profesional'],
                rut=validated_data['rut_profesional'],
                email=validated_data['email_profesional'],
                telefono=validated_data['telefono_profesional'],
                password=validated_data['password'],
                numero_registro_salud=validated_data.get('numero_registro_salud_profesional'),
            )
        except DjangoValidationError as error:
            detalle = error.message_dict if hasattr(error, 'message_dict') else error.messages
            raise serializers.ValidationError(detalle)


class PM_ProfesionalSerializer(serializers.ModelSerializer):
    """
    Vista completa del propio perfil (autenticado) o del detalle administrativo.
    Nunca expone password_profesional. Los campos sensibles/administrativos son
    de solo lectura: se editan mediante endpoints dedicados con sus propias
    validaciones (editar datos, cambiar contraseña, resolver acreditación, etc.).
    """
    acreditaciones = PM_AcreditacionSerializer(many=True, read_only=True)
    documentos = PM_Documento_RespaldoSerializer(many=True, read_only=True)
    especialidades_asignadas = PM_Profesional_especialidadSerializer(
        source='profesional_especialidades', many=True, read_only=True
    )

    class Meta:
        model = PM_Profesional
        fields = [
            'id_profesional', 'nombres_profesional', 'apellidos_profesional', 'rut_profesional',
            'numero_registro_salud_profesional', 'email_profesional', 'telefono_profesional',
            'estado_cuenta_profesional', 'fecha_creacion', 'fecha_actualizacion',
            'acreditaciones', 'documentos', 'especialidades_asignadas',
        ]
        read_only_fields = [
            'id_profesional', 'rut_profesional', 'estado_cuenta_profesional',
            'fecha_creacion', 'fecha_actualizacion',
        ]


class PM_ProfesionalDirectorioSerializer(serializers.ModelSerializer):
    """
    Vista pública (sin autenticar) usada para que los pacientes encuentren
    fonoaudiólogos ya acreditados. Solo se sirve a profesionales verificados
    (ver PM_ProfesionalQueryset.verificados) y no incluye datos administrativos.
    """
    especialidades = PM_EspecialidadSerializer(many=True, read_only=True)

    class Meta:
        model = PM_Profesional
        fields = [
            'id_profesional', 'nombres_profesional', 'apellidos_profesional',
            'numero_registro_salud_profesional', 'email_profesional', 'telefono_profesional',
            'especialidades',
        ]


class PM_ProfesionalLoginSerializer(serializers.Serializer):
    identificador = serializers.CharField(help_text='Email o RUT del profesional')
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class PM_ProfesionalCambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nueva = serializers.CharField(write_only=True, min_length=8)
