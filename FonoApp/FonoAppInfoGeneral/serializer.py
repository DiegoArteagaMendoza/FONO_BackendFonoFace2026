from rest_framework import serializers
from .models import FonoApp_InfoGeneral

class FonoApp_InfoGeneralSerializer(serializers.ModelSerializer):
    class Meta:
        model = FonoApp_InfoGeneral
        fields = '__all__'
        read_only_fields = ['id_info', 'fecha_creacion', 'fecha_actualizacion', 'usuario_registro']

    def create(self, validated_data):
        # Inyectamos automáticamente al usuario que está haciendo la petición
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['usuario_registro'] = request.user
        return super().create(validated_data)