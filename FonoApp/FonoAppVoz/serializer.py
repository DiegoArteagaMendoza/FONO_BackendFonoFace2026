from rest_framework import serializers
from FonoAppVoz.models import FonoApp_Voz
from FonoAppFunciones.archivos import url_absoluta

class FonoApp_VozSerializer(serializers.ModelSerializer):
    # Entrega el string legible del Enum (ej: "Anatomía" en vez de "ANATOMIA")
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)

    class Meta:
        model = FonoApp_Voz
        fields = [
            'id_voz', 'categoria', 'categoria_display', 'titulo',
            'contenido', 'img', 'fuente', 'estado', 'FonoApp_Administracion'
        ]
        read_only_fields = ['id_voz', 'estado', 'FonoApp_Administracion']

    def to_representation(self, instance):
        """
        La imagen es un CloudinaryField: serializado tal cual entrega el
        public_id, no una URL. Se reemplaza por la URL https real para que
        la seccion de la voz pueda mostrarla.
        """
        datos = super().to_representation(instance)
        datos['img'] = url_absoluta(instance.img)
        return datos

    def create(self, validated_data):
        usuario = self.context['request'].user
        return FonoApp_Voz.objects.crear_voz(usuario=usuario, **validated_data)
