from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from Security.permissions import EsAdministrador, EsProfesional
from PmMedico.models import Administrador, PM_Profesional
from PmCita.models import PmCita
from PmCita.serializer import (
    PmCitaSerializer,
    PmCitaReservarSerializer,
    PmCitaClienteCancelarSerializer,
    PmCitaClientePosponerSerializer,
    PmCitaCancelarSerializer,
    PmCitaPosponerSerializer,
)


def _respuesta_error(error, mensaje_404='no encontrada'):
    codigo = status.HTTP_404_NOT_FOUND if mensaje_404 in error else status.HTTP_400_BAD_REQUEST
    return Response({'error': error}, status=codigo)


# ==========================================================================
# RESERVA Y GESTIÓN DEL LADO DEL CLIENTE
# --------------------------------------------------------------------------
# TODO: igual que en PmCliente/PmVideo, cuando el Portal Médico tenga sesión
# propia para clientes, todo este bloque debe exigir autenticación y tomar
# al cliente del token en vez de recibirlo en el cuerpo de la petición, para
# que nadie pueda reservar, cancelar ni posponer citas a nombre de otro.
# ==========================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def cita_reservar(request):
    """
    Reserva una cita. Valida que el profesional esté acreditado, que la hora
    tenga la anticipación mínima y que no se cruce con otra cita del mismo
    profesional.
    """
    entrada = PmCitaReservarSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    datos = entrada.validated_data

    try:
        cita = PmCita.objects.reservar(
            cliente=datos['id_cliente'],
            profesional=datos['id_profesional'],
            fecha_hora=datos['fecha_hora'],
            motivo_consulta=datos.get('motivo_consulta', ''),
            duracion_minutos=datos.get('duracion_minutos'),
        )
    except DjangoValidationError as error:
        detalle = error.message_dict if hasattr(error, 'message_dict') else error.messages
        return Response({'error': detalle}, status=status.HTTP_400_BAD_REQUEST)

    return Response(PmCitaSerializer(cita).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def citas_cliente_listar(request, id_cliente):
    """
    Historial de citas de un cliente.
    ?proximas=true filtra solo las activas y futuras; sin ese parámetro,
    entrega todo el historial (incluye canceladas y realizadas).
    """
    if request.query_params.get('proximas', '').lower() == 'true':
        citas = PmCita.objects.proximas_de_cliente(id_cliente)
    else:
        citas = PmCita.objects.de_cliente(id_cliente)

    return Response(PmCitaSerializer(citas, many=True).data)


@api_view(['PATCH'])
@permission_classes([AllowAny])
def cita_cliente_cancelar(request, id_cita):
    """El cliente cancela su propia cita (no la realizará)."""
    entrada = PmCitaClienteCancelarSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)

    cita, error = PmCita.objects.cancelar_por_cliente(
        id_cita, entrada.validated_data['id_cliente'].pk, entrada.validated_data.get('motivo')
    )
    if error:
        return _respuesta_error(error)

    return Response(PmCitaSerializer(cita).data)


@api_view(['PATCH'])
@permission_classes([AllowAny])
def cita_cliente_posponer(request, id_cita):
    """El cliente reprograma su propia cita a una nueva fecha/hora."""
    entrada = PmCitaClientePosponerSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)

    cita, error = PmCita.objects.posponer_por_cliente(
        id_cita,
        entrada.validated_data['id_cliente'].pk,
        entrada.validated_data['fecha_hora'],
        entrada.validated_data.get('motivo'),
    )
    if error:
        return _respuesta_error(error)

    return Response(PmCitaSerializer(cita).data)


# ==========================================================================
# GESTIÓN DEL LADO DEL PROFESIONAL (autenticado)
# ==========================================================================

@api_view(['GET'])
@permission_classes([EsProfesional])
def citas_profesional_listar(request):
    """
    Citas del profesional autenticado.
    ?proximas=true filtra solo las activas y futuras; sin ese parámetro,
    entrega todo su historial.
    """
    if request.query_params.get('proximas', '').lower() == 'true':
        citas = PmCita.objects.proximas_de_profesional(request.user.pk)
    else:
        citas = PmCita.objects.de_profesional(request.user.pk)

    return Response(PmCitaSerializer(citas, many=True).data)


@api_view(['PATCH'])
@permission_classes([EsProfesional])
def cita_profesional_cancelar(request, id_cita):
    """El profesional cancela una cita propia."""
    entrada = PmCitaCancelarSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)

    cita, error = PmCita.objects.cancelar_por_profesional(
        id_cita, request.user.pk, entrada.validated_data.get('motivo')
    )
    if error:
        return _respuesta_error(error)

    return Response(PmCitaSerializer(cita).data)


@api_view(['PATCH'])
@permission_classes([EsProfesional])
def cita_profesional_posponer(request, id_cita):
    """El profesional reprograma una cita propia a una nueva fecha/hora."""
    entrada = PmCitaPosponerSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)

    cita, error = PmCita.objects.posponer_por_profesional(
        id_cita, request.user.pk, entrada.validated_data['fecha_hora'], entrada.validated_data.get('motivo')
    )
    if error:
        return _respuesta_error(error)

    return Response(PmCitaSerializer(cita).data)


@api_view(['PATCH'])
@permission_classes([EsProfesional])
def cita_profesional_marcar_realizada(request, id_cita):
    """El profesional confirma que la atención se llevó a cabo."""
    cita, error = PmCita.objects.marcar_realizada(id_cita, request.user.pk)
    if error:
        return _respuesta_error(error)

    return Response(PmCitaSerializer(cita).data)


# ==========================================================================
# DETALLE Y ADMINISTRACIÓN
# ==========================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def cita_detalle(request, id_cita):
    """
    Retorna el detalle de una cita puntual. Acceso permitido a:
      - el profesional dueño de la cita o un administrador (autenticados), o
      - el cliente dueño, identificado con ?cliente=<id_cliente> (mismo
        modelo de confianza que el resto de los endpoints de cliente; ver
        el TODO al inicio de este archivo).
    """
    try:
        cita = PmCita.objects.get(pk=id_cita)
    except PmCita.DoesNotExist:
        return Response({'error': 'Cita no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    usuario = request.user
    es_profesional_dueno = isinstance(usuario, PM_Profesional) and usuario.pk == cita.profesional_id
    es_administrador = isinstance(usuario, Administrador) and usuario.is_staff

    id_cliente_param = request.query_params.get('cliente')
    es_cliente_dueno = id_cliente_param is not None and str(cita.cliente_id) == str(id_cliente_param)

    if not (es_profesional_dueno or es_administrador or es_cliente_dueno):
        return Response({'error': 'No tiene permiso para ver esta cita'}, status=status.HTTP_403_FORBIDDEN)

    return Response(PmCitaSerializer(cita).data)


@api_view(['GET'])
@permission_classes([EsAdministrador])
def citas_listar(request):
    """
    Listado administrativo completo. Filtros opcionales combinables:
    ?cliente=<id_cliente>  ?profesional=<id_profesional>  ?estado=RE|CC|CM|RZ
    """
    citas = PmCita.objects.all()

    id_cliente = request.query_params.get('cliente')
    if id_cliente:
        citas = citas.filter(cliente_id=id_cliente)

    id_profesional = request.query_params.get('profesional')
    if id_profesional:
        citas = citas.filter(profesional_id=id_profesional)

    estado = request.query_params.get('estado')
    if estado:
        citas = citas.filter(estado=estado)

    return Response(PmCitaSerializer(citas, many=True).data)
