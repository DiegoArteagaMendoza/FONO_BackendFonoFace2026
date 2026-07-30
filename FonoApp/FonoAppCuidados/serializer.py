from rest_framework import serializers
from FonoAppCuidados.models import FonoApp_Cuidados

class FonoApp_CuidadosSerializer(serializers.ModelSerializer):
    # Entrega el string legible del Enum (ej: "Cantantes y/o Actores" en vez de "CANTANTES_ACTORES")
    publico_display = serializers.CharField(source='get_publico_display', read_only=True)

    class Meta:
        model = FonoApp_Cuidados
        fields = [
            'id_cuidado', 'publico', 'publico_display', 'titulo', 
            'contenido', 'img', 'fuente', 'estado', 'FonoApp_Administracion'
        ]
        read_only_fields = ['id_cuidado', 'estado', 'FonoApp_Administracion']
        
    def create(self, validated_data):
        usuario = self.context['request'].user
        return FonoApp_Cuidados.objects.crear_cuidado(usuario=usuario, **validated_data)