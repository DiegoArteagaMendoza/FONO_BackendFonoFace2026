from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from Security.permissions import EsAdministrador, EsCliente, EsProfesional
from PmCliente.models import PmCliente
from PmCliente.serializer import (
    PmClienteRegistroSerializer,
    PmClienteSerializer,
    PmClienteLoginSerializer,
    PmClienteCambiarPasswordSerializer,
)


# =========================================================================
# PACIENTE: registro, sesión y perfil propio
# =========================================================================

@api_view(['POST'])
@permission_classes([AllowAny])  # Cualquier persona debe poder registrarse
def cliente_registrar(request):
    """
    Registra a una persona que quiere optar a atenciones telemáticas y le crea
    su contraseña para que después pueda iniciar sesión.
    """
    serializer = PmClienteRegistroSerializer(data=request.data)

    if serializer.is_valid():
        cliente = serializer.save()
        return Response(PmClienteSerializer(cliente).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def cliente_login(request):
    """Autentica por correo o RUT + contraseña y entrega un JWT propio del paciente."""
    credenciales = PmClienteLoginSerializer(data=request.data)
    credenciales.is_valid(raise_exception=True)

    cliente = PmCliente.objects.autenticar(
        credenciales.validated_data['identificador'],
        credenciales.validated_data['password'],
    )

    if not cliente:
        return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken()
    refresh['id_cliente'] = cliente.pk
    access = refresh.access_token

    return Response({
        'refresh': str(refresh),
        'access': str(access),
        'cliente': {
            'id_cliente': cliente.pk,
            'nombres_cliente': cliente.nombres_cliente,
            'apellidos_clientes': cliente.apellidos_clientes,
            'email_cliente': cliente.email_cliente,
        },
    })


@api_view(['GET'])
@permission_classes([EsCliente])
def cliente_perfil(request):
    """Datos del paciente autenticado (los toma del token, no de la URL)."""
    return Response(PmClienteSerializer(request.user).data)


@api_view(['PATCH'])
@permission_classes([EsCliente])
def cliente_perfil_editar(request):
    """
    Edita los datos de contacto propios. El RUT, la contraseña y el estado de la
    cuenta NO se pueden tocar desde aquí.
    """
    campos_editables = (
        'nombres_cliente', 'apellidos_clientes', 'fecha_nacimiento_cliente',
        'email_cliente', 'telefono_cliente',
    )
    datos_a_actualizar = {campo: request.data[campo] for campo in campos_editables if campo in request.data}

    if not datos_a_actualizar:
        return Response({'error': 'Debe enviar al menos un campo editable'}, status=status.HTTP_400_BAD_REQUEST)

    # Validamos formato con el serializer antes de persistir
    validador = PmClienteSerializer(request.user, data=datos_a_actualizar, partial=True)
    validador.is_valid(raise_exception=True)

    PmCliente.objects.editar_cliente(request.user.pk, **validador.validated_data)

    request.user.refresh_from_db()
    return Response(PmClienteSerializer(request.user).data)


@api_view(['PUT'])
@permission_classes([EsCliente])
def cliente_cambiar_password(request):
    """Cambia la contraseña propia; exige la actual para evitar el secuestro de sesión."""
    datos = PmClienteCambiarPasswordSerializer(data=request.data)
    datos.is_valid(raise_exception=True)

    cliente = request.user

    if not cliente.check_password(datos.validated_data['password_actual']):
        return Response({'error': 'La contraseña actual no es correcta'}, status=status.HTTP_400_BAD_REQUEST)

    cliente.set_password(datos.validated_data['password_nueva'])
    cliente.save(update_fields=['password_cliente'])

    return Response({'mensaje': 'Contraseña actualizada correctamente'}, status=status.HTTP_200_OK)


# ==========================================================================
# GESTIÓN (profesional que atiende / administrador)
# --------------------------------------------------------------------------
# Exponen datos personales del paciente (RUT, correo, teléfono), por eso usan
# los roles definidos en Security/permissions.py:
#   - Consultar: el profesional que atiende o un administrador.
#   - Modificar/eliminar: solo administrador.
# ==========================================================================

@api_view(['GET'])
@permission_classes([EsProfesional | EsAdministrador])
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
@permission_classes([EsProfesional | EsAdministrador])
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
@permission_classes([EsAdministrador])
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
@permission_classes([EsAdministrador])
def cliente_eliminar(request, id_cliente):
    """
    Realiza un borrado lógico del cliente.
    """
    actualizado = PmCliente.objects.eliminar_logico(id_cliente)

    if actualizado:
        return Response({'mensaje': 'Cliente eliminado correctamente'}, status=status.HTTP_200_OK)

    return Response({'error': 'Cliente no encontrado o ya eliminado'}, status=status.HTTP_404_NOT_FOUND)
