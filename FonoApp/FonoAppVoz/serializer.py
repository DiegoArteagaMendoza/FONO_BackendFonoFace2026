from rest_framework import serializers
from FonoAppVoz.models import FonoApp_Voz

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

    def create(self, validated_data):
        usuario = self.context['request'].user
        return FonoApp_Voz.objects.crear_voz(usuario=usuario, **validated_data)
