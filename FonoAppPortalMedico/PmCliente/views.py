from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from PmCliente.models import PmCliente
from PmCliente.serializer import PmClienteSerializer


# ==========================================
# ENDPOINT PÚBLICO (registro de pacientes)
# ==========================================

@api_view(['POST'])
@permission_classes([AllowAny])  # Cualquier persona debe poder registrarse
def cliente_registrar(request):
    """
    Registra a una persona que quiere optar a atenciones telemáticas.
    """
    serializer = PmClienteSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================================================
# ENDPOINTS DE GESTIÓN (protegidos)
# --------------------------------------------------------------------------
# Estos endpoints exponen datos personales (RUT, correo, teléfono), por eso
# exigen autenticación. IMPORTANTE: el Portal Médico todavía no tiene su
# autenticación resuelta, así que hoy responden 403. Cuando se defina el
# esquema de login del portal basta con agregar aquí su clase de
# autenticación (como hace FonoApp con CustomJWTAuthentication).
# ==========================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def clientes_listar(request):
    """
    Lista los clientes activos. Admite búsqueda con ?buscar=texto
    """
    texto = request.query_params.get('buscar', None)

    if texto:
        clientes = PmCliente.objects.buscar(texto)
    else:
        clientes = PmCliente.objects.activos()

    serializer = PmClienteSerializer(clientes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cliente_detalle(request, id_cliente):
    """
    Retorna los datos de un cliente puntual.
    """
    try:
        cliente = PmCliente.objects.get(pk=id_cliente, estado=True)
    except PmCliente.DoesNotExist:
        return Response({'error': 'Cliente no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    serializer = PmClienteSerializer(cliente)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def cliente_editar(request, id_cliente):
    """
    Edita los datos de un cliente activo.
    """
    try:
        cliente = PmCliente.objects.get(pk=id_cliente, estado=True)
    except PmCliente.DoesNotExist:
        return Response({'error': 'Cliente no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    serializer = PmClienteSerializer(cliente, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({'mensaje': 'Cliente actualizado correctamente', 'data': serializer.data},
                        status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cliente_eliminar(request, id_cliente):
    """
    Realiza un borrado lógico del cliente.
    """
    actualizado = PmCliente.objects.eliminar_logico(id_cliente)

    if actualizado:
        return Response({'mensaje': 'Cliente eliminado correctamente'}, status=status.HTTP_200_OK)

    return Response({'error': 'Cliente no encontrado o ya eliminado'}, status=status.HTTP_404_NOT_FOUND)
