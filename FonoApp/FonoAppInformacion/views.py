from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from FonoAppInformacion.models import FonoApp_Informacion
from FonoAppInformacion.serializer import FonoApp_InformacionSerializer
from FonoAppFunciones.authentication import CustomJWTAuthentication

# =========================================================
# 1. LISTAR Y FILTRAR
# =========================================================
@api_view(['GET'])
@permission_classes([AllowAny]) # Dejado público para lectura, cámbialo a IsAuthenticated si es privado
def informacion_listar(request):
    """
    Lista toda la información activa. 
    Permite filtrar por categoría si se envía en la URL.
    Ejemplo: /api/informacion/listar/?categoria=SA
    """
    # Traemos la data base ya optimizada (sin N+1)
    queryset = FonoApp_Informacion.objects.activas().con_detalles()

    # Si el front envía una categoría en la query string (?categoria=SA), filtramos
    categoria_codigo = request.query_params.get('categoria')
    if categoria_codigo:
        queryset = queryset.por_categoria(categoria_codigo)

    serializer = FonoApp_InformacionSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# =========================================================
# 2. CREAR
# =========================================================
@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def informacion_crear(request):
    """
    Crea un nuevo registro de información. Soporta hasta 4 imágenes.
    """
    # Pasamos el request al context para que el serializer sepa quién es el usuario
    serializer = FonoApp_InformacionSerializer(
        data=request.data, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save() # Dispara el método create() de tu serializer y QuerySet
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================================================
# 3. EDITAR TEXTO (PUT / PATCH)
# =========================================================
@api_view(['PUT', 'PATCH'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def informacion_editar(request, id_informacion):
    """
    Edita los campos de texto de un registro (título, categoría, contenido).
    No procesa imágenes (esas deben manejarse en un endpoint aparte si se requiere editarlas).
    """
    try:
        informacion = FonoApp_Informacion.objects.get(id_informacion=id_informacion, estado=True)
    except FonoApp_Informacion.DoesNotExist:
        return Response({'error': 'Registro no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    # Usamos el serializer con partial=True para validar los datos que lleguen
    serializer = FonoApp_InformacionSerializer(informacion, data=request.data, partial=True)
    
    if serializer.is_valid():
        datos_validados = serializer.validated_data
        
        # Ejecutamos el método altamente eficiente de tu QuerySet
        actualizado = FonoApp_Informacion.objects.editar_informacion(
            id_informacion=id_informacion,
            **datos_validados
        )
        
        if actualizado:
            # Traemos la información fresca de la BD para responder con los datos actualizados
            informacion.refresh_from_db()
            response_serializer = FonoApp_InformacionSerializer(informacion)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        return Response({'error': 'No se pudo actualizar el registro'}, status=status.HTTP_400_BAD_REQUEST)
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================================================
# 4. ELIMINAR (BORRADO LÓGICO)
# =========================================================
@api_view(['DELETE'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def informacion_eliminar(request, id_informacion):
    """
    Realiza un borrado lógico del registro.
    """
    actualizado = FonoApp_Informacion.objects.eliminar_logico(id_informacion)
    
    if actualizado:
        return Response({'mensaje': 'Información eliminada correctamente'}, status=status.HTTP_200_OK)
        
    return Response({'error': 'Registro no encontrado o ya eliminado'}, status=status.HTTP_404_NOT_FOUND)