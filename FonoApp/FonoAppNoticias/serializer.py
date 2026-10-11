from rest_framework import serializers
from FonoAppNoticias.models import FonoApp_Noticias, FonoApp_Noticia_Imagen, FonoApp_Newsletter
from FonoAppFunciones.archivos import url_absoluta

# 1. Serializer secundario para formatear la salida de las imágenes en el GET
class FonoApp_Noticia_ImagenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FonoApp_Noticia_Imagen
        fields = ['id', 'imagen', 'fecha_subida']

    def to_representation(self, instance):
        """
        La imagen es un CloudinaryField: serializado tal cual entrega el
        public_id, no una URL. Se reemplaza por la URL https real para que
        el portal de noticias pueda mostrarla.
        """
        datos = super().to_representation(instance)
        datos['imagen'] = url_absoluta(instance.imagen)
        return datos


# 2. Serializer principal de la Noticia
class FonoApp_NoticiasSerializer(serializers.ModelSerializer):
    # Campo de solo lectura para anidar los datos de las imágenes en el GET
    # El nombre 'imagenes' DEBE coincidir con el related_name qde ForeignKey
    imagenes = FonoApp_Noticia_ImagenSerializer(many=True, read_only=True)
    
    # Campo de solo escritura para recibir los archivos físicos desde el Frontend (POST)
    imagenes_subidas = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        write_only=True,
        required=False # Es False para permitir noticias sin imágenes (0 a 4)
    )

    class Meta:
        model = FonoApp_Noticias
        fields = [
            'id_noticia', 'titulo', 'contenido', 'fecha_creacion', 
            'fecha_actualizacion', 'estado', 'FonoApp_Administracion', 
            'imagenes', 'imagenes_subidas'
        ]
        # El frontend no debe enviar ni modificar estos campos:
        read_only_fields = [
            'id_noticia', 'fecha_creacion', 'fecha_actualizacion', 
            'estado', 'FonoApp_Administracion'
        ]

    def validate_imagenes_subidas(self, value):
        """
        Validación temprana: Frenamos la petición si vienen más de 4 imágenes
        antes de siquiera tocar la base de datos.
        """
        if len(value) > 4:
            raise serializers.ValidationError("Solo se permiten hasta 4 imágenes por noticia.")
        return value

    def create(self, validated_data):
        # 1. Extraemos los archivos de imagen (si los enviaron)
        imagenes = validated_data.pop('imagenes_subidas', None)
        
        # 2. Obtenemos al usuario que está haciendo la petición desde el token JWT.
        # Esto es más seguro que pedirle al frontend que mande su ID.
        usuario = self.context['request'].user
        
        # 3. creamos la noticia
        return FonoApp_Noticias.objects.crear_noticia(
            usuario=usuario,
            titulo=validated_data.get('titulo'),
            contenido=validated_data.get('contenido'),
            imagenes=imagenes
        )

# 3. Serializer para las suscripciones al Newsletter
class FonoApp_NewsletterSerializer(serializers.ModelSerializer):
    class Meta:
        model = FonoApp_Newsletter
        fields = ['id_suscripcion', 'email', 'fecha_suscripcion', 'estado']
        read_only_fields = ['id_suscripcion', 'fecha_suscripcion', 'estado']
