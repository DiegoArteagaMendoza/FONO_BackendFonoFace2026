from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from FonoAppNoticias.models import FonoApp_Noticias, FonoApp_Noticia_Imagen, FonoApp_Newsletter
from FonoAppNoticias.serializer import FonoApp_NoticiasSerializer, FonoApp_NewsletterSerializer
from FonoAppFunciones.authentication import CustomJWTAuthentication
from FonoAppFunciones.archivos import borrar_de_cloudinary

@api_view(['GET'])
@permission_classes([AllowAny]) # Lo dejo público para que cualquiera pueda leer las noticias, cámbialo a IsAuthenticated si es privado
def noticias_listar(request):
    """
    Lista todas las noticias activas con sus imágenes.
    Aprovecha el select_related y prefetch_related para máxima velocidad.
    """
    noticias = FonoApp_Noticias.objects.activas().con_detalles()
    serializer = FonoApp_NoticiasSerializer(noticias, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def noticias_crear(request):
    """
    Crea una noticia nueva y asocia las imágenes subidas.
    """
    # ¡MUY IMPORTANTE! Pasamos el context={'request': request} 
    # para que el Serializer pueda sacar el usuario del token.
    serializer = FonoApp_NoticiasSerializer(
        data=request.data, 
        context={'request': request} 
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def noticia_eliminar(request, id_noticia):
    """
    Realiza un borrado lógico de la noticia.
    """
    actualizado = FonoApp_Noticias.objects.eliminar_logico(id_noticia)
    
    if actualizado:
        return Response({'mensaje': 'Noticia eliminada correctamente'}, status=status.HTTP_200_OK)
        
    return Response({'error': 'Noticia no encontrada o ya eliminada'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT', 'PATCH']) # Soportamos PUT (reemplazo total) y PATCH (reemplazo parcial)
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def noticia_editar(request, id_noticia):
    """
    Edita los campos de texto de una noticia (título y/o contenido).
    """
    # Filtramos para enviar al queryset solo los campos que nos interesan actualizar
    datos_a_actualizar = {}
    
    if 'titulo' in request.data:
        datos_a_actualizar['titulo'] = request.data['titulo']
        
    if 'contenido' in request.data:
        datos_a_actualizar['contenido'] = request.data['contenido']
        
    # Si el frontend no mandó ni título ni contenido, evitamos hacer una consulta inútil
    if not datos_a_actualizar:
        return Response(
            {'error': 'Debe proporcionar al menos un campo (titulo o contenido) para actualizar'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
        
    # Llamamos a nuestro método eficiente del queryset
    actualizado = FonoApp_Noticias.objects.editar_noticia(id_noticia, **datos_a_actualizar)
    
    if actualizado:
        return Response({'mensaje': 'Noticia actualizada correctamente'}, status=status.HTTP_200_OK)
        
    return Response({'error': 'Noticia no encontrada o se encuentra inactiva'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def noticia_imagen_agregar(request, id_noticia):
    """
    Recibe nuevas imágenes y las asocia a una noticia existente.
    """
    # Usamos getlist para capturar todos los archivos enviados en el FormData
    nuevas_imagenes = request.FILES.getlist('imagenes_subidas')
    
    if not nuevas_imagenes:
        return Response({'error': 'No se adjuntaron imágenes en la petición'}, status=status.HTTP_400_BAD_REQUEST)
        
    exito, mensaje = FonoApp_Noticias.objects.agregar_imagenes(id_noticia, nuevas_imagenes)
    
    if exito:
        return Response({'mensaje': mensaje}, status=status.HTTP_201_CREATED)
        
    return Response({'error': mensaje}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def noticia_imagen_eliminar(request, id_imagen):
    """
    Elimina físicamente una imagen del servidor y su registro de la base de datos.
    Nota: Recibe el ID de la imagen, no de la noticia.
    """
    try:
        imagen = FonoApp_Noticia_Imagen.objects.get(id=id_imagen)
        # 1. Borramos el archivo de Cloudinary. No sirve imagen.delete(save=False):
        #    un CloudinaryField guarda un CloudinaryResource, que no tiene ese
        #    metodo y lanzaria AttributeError.
        borrar_de_cloudinary(imagen.imagen)
        # 2. Borramos el registro de la tabla FonoApp_Noticia_Imagen
        imagen.delete() 
        return Response({'mensaje': 'Imagen eliminada correctamente'}, status=status.HTTP_200_OK)
        
    except FonoApp_Noticia_Imagen.DoesNotExist:
        return Response({'error': 'La imagen no existe'}, status=status.HTTP_404_NOT_FOUND)
@api_view(['POST'])
@permission_classes([AllowAny]) # Público: cualquier visitante del portal puede suscribirse
def newsletter_suscribir(request):
    """
    Registra un correo en el newsletter.
    Si el correo ya existe pero estaba desactivado, se reactiva.
    """
    email = request.data.get('email', '').strip().lower()

    if not email:
        return Response({'error': 'El correo electrónico es obligatorio'}, status=status.HTTP_400_BAD_REQUEST)

    # Si ya existe, no duplicamos: reactivamos si estaba dado de baja
    suscripcion_existente = FonoApp_Newsletter.objects.filter(email=email).first()
    if suscripcion_existente:
        if not suscripcion_existente.estado:
            suscripcion_existente.estado = True
            suscripcion_existente.save(update_fields=['estado'])
            return Response({'mensaje': 'Suscripción reactivada correctamente'}, status=status.HTTP_200_OK)
        return Response({'mensaje': 'Este correo ya se encuentra suscrito'}, status=status.HTTP_200_OK)

    serializer = FonoApp_NewsletterSerializer(data={'email': email})
    if serializer.is_valid():
        serializer.save()
        return Response({'mensaje': 'Suscripción registrada correctamente'}, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
