from rest_framework import serializers
from FonoAppCuidados.models import FonoApp_Cuidados
from FonoAppFunciones.archivos import url_absoluta

class FonoApp_CuidadosSerializer(serializers.ModelSerializer):
    # Entrega el string legible del Enum (ej: "Cantantes y/o Actores" en vez de "CANTANTES_ACTORES")
    publico_display = serializers.CharField(source='get_publico_display', read_only=True)

    class Meta:
        model = FonoApp_Cuidados
        fields = [
            'id_cuidado', 'publico', 'publico_display', 'titulo',
            'contenido', 'img', 'fuente', 'estado', 'fecha_creacion', 'FonoApp_Administracion'
        ]
        read_only_fields = ['id_cuidado', 'estado', 'fecha_creacion', 'FonoApp_Administracion']

    def to_representation(self, instance):
        """
        La imagen es un CloudinaryField: serializado tal cual entrega el
        public_id, no una URL. Se reemplaza por la URL https real para que
        el portal de cuidados pueda mostrarla.
        """
        datos = super().to_representation(instance)
        datos['img'] = url_absoluta(instance.img)
        return datos
        
    def create(self, validated_data):
        usuario = self.context['request'].user
        return FonoApp_Cuidados.objects.crear_cuidado(usuario=usuario, **validated_data)