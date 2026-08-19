from rest_framework import serializers
from FonoAppInformacion.models import FonoApp_Informacion, FonoApp_Informacion_Imagen

# 1. Serializer secundario para formatear la salida de las imágenes en el GET
class FonoApp_Informacion_ImagenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FonoApp_Informacion_Imagen
        fields = ['id', 'imagen', 'fecha_subida']


# 2. Serializer principal de la Información
class FonoApp_InformacionSerializer(serializers.ModelSerializer):
    # Anidamos las imágenes para las respuestas GET
    imagenes = FonoApp_Informacion_ImagenSerializer(many=True, read_only=True)
    
    # Campo para recibir los archivos físicos desde el Frontend (POST)
    imagenes_subidas = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        write_only=True,
        required=False # Es False para permitir crear información sin imágenes
    )

    # Campo extra de solo lectura que devuelve el nombre legible de la categoría
    # Ejemplo: en vez de devolver "SA", devuelve "Salud Animal"
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)

    class Meta:
        model = FonoApp_Informacion
        fields = [
            'id_informacion', 'titulo', 'categoria', 'categoria_display', 
            'contenido', 'fecha_creacion', 'fecha_actualizacion', 'estado', 
            'FonoApp_Administracion', 'imagenes', 'imagenes_subidas'
        ]
        
        # Protegemos los campos que el frontend no debe enviar ni modificar
        read_only_fields = [
            'id_informacion', 'fecha_creacion', 'fecha_actualizacion', 
            'estado', 'FonoApp_Administracion'
        ]

    def validate_imagenes_subidas(self, value):
        """
        Validación: Máximo 4 imágenes y solo formatos admitidos.
        """
        if len(value) > 4:
            raise serializers.ValidationError("Solo se permiten hasta 4 imágenes por registro.")
        
        # Validar formatos permitidos
        formatos_permitidos = ['image/jpeg', 'image/png']
        for img in value:
            if img.content_type not in formatos_permitidos:
                raise serializers.ValidationError(
                    f"El formato del archivo '{img.name}' no está permitido. Solo se aceptan imágenes JPG, JPEG y PNG."
                )
                
        return value

    def create(self, validated_data):
        # Extraemos las imágenes si fueron enviadas
        imagenes = validated_data.pop('imagenes_subidas', None)
        
        # Obtenemos al usuario desde el token JWT
        usuario = self.context['request'].user
        
        # Llamamos al método del QuerySet (asumiendo que crearás uno similar al de noticias)
        return FonoApp_Informacion.objects.crear_informacion(
            usuario=usuario,
            titulo=validated_data.get('titulo'),
            categoria=validated_data.get('categoria'),
            contenido=validated_data.get('contenido'),
            imagenes=imagenes
        )