from rest_framework import serializers
from FonoAppAdministracion.models import FonoApp_Administracion, FonoApp_Banner_Inicio, FonoApp_Banner_Inicio_Imagenes

class FonoApp_Banner_ImagenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FonoApp_Banner_Inicio_Imagenes
        fields = ['id', 'imagen', 'fecha_subida']


class FonoApp_Banner_InicioSerializer(serializers.ModelSerializer): 
    imagenes = FonoApp_Banner_ImagenSerializer(many=True, read_only=True)

    class Meta:
        model = FonoApp_Banner_Inicio
        fields = [
            'id_banner', 'titulo', 'descripcion', 'fecha_creacion', 
            'fecha_actualizacion', 'estado', 'FonoApp_Administracion', 
            'imagenes'
        ]
        read_only_fields = [
            'id_banner', 'fecha_creacion', 'fecha_actualizacion', 'estado', 'FonoApp_Administracion'
        ]
        
    def create(self, validated_data):
        # 2. Recuperamos el request original que inyectamos desde la vista
        request = self.context.get('request')
        usuario = request.user
        
        # 3. TRUCO DE ORO: Extraemos el archivo directamente de la petición cruda.
        # getlist() asegura que capturemos el archivo aunque venga desde un FormData de Angular
        imagenes = request.FILES.getlist('imagenes_subidas')
        
        # 4. Validamos aquí para retornar un error 400 limpio si mandan más de 1 foto
        if len(imagenes) > 1:
            raise serializers.ValidationError({
                "imagenes_subidas": "Solo se permite adjuntar una (1) imagen por banner."
            })
        
        # 5. Enviamos la información limpia a tu QuerySet
        return FonoApp_Banner_Inicio.objects.crear_banner(
            usuario=usuario,
            titulo=validated_data.get('titulo'),
            descripcion=validated_data.get('descripcion'),
            imagenes=imagenes
        )

class FonoApp_Serializer(serializers.ModelSerializer):
    # Añadimos el estilo de password para la interfaz web
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = FonoApp_Administracion
        fields = ['id_usuario', 'nombre', 'rut', 'email', 'tipo', 'estado', 'is_staff', 'password', 'last_conection']
        read_only_fields = ['id_usuario']

    def create(self, validated_data):
        # Llamamos al método personalizado del QuerySet
        return FonoApp_Administracion.objects.crear_usuario(**validated_data)

    def update(self, instance, validated_data):
        # Extraemos el password del diccionario de datos (si no viene, devuelve None)
        password = validated_data.pop('password', None)
        
        # Dejamos que DRF actualice el resto de los campos (nombre, rut, etc.)
        # Esto maneja automáticamente la lógica de PUT vs PATCH
        instance = super().update(instance, validated_data)
        
        # Si en la petición enviaron un password, lo encriptamos
        if password:
            instance.set_password(password) # set_password encripta automáticamente
            instance.save() # Guardamos el cambio de la contraseña
            
        return instance