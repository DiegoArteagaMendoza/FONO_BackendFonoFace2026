from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from Security.permissions import EsAdministrador, EsCliente, EsProfesional
from PmMedico.models import Administrador, PM_Profesional
from PmCliente.models import PmCliente
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
# RESERVA Y GESTIÓN DEL LADO DEL CLIENTE (paciente autenticado)
# --------------------------------------------------------------------------
# Igual que en PmCliente/PmVideo, el paciente se identifica con su propio
# token (Security.authentication reconoce el claim id_cliente) y el dueño de
# la cita se toma SIEMPRE de request.user, nunca del cuerpo de la petición:
# así nadie puede reservar, cancelar ni posponer citas a nombre de otro con
# solo conocer su id_cliente.
# ==========================================================================

@api_view(['POST'])
@permission_classes([EsCliente])
def cita_reservar(request):
    """
    El paciente autenticado reserva una cita. Valida que el profesional esté
    acreditado, que la hora tenga la anticipación mínima y que no se cruce con
    otra cita del mismo profesional.
    """
    entrada = PmCitaReservarSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    datos = entrada.validated_data

    try:
        cita = PmCita.objects.reservar(
            cliente=request.user,
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
@permission_classes([EsCliente])
def citas_cliente_listar(request, id_cliente):
    """
    Historial de citas del paciente autenticado.
    ?proximas=true filtra solo las activas y futuras; sin ese parámetro,
    entrega todo el historial (incluye canceladas y realizadas).

    El id_cliente sigue en la URL por compatibilidad, pero solo se acepta si
    coincide con el dueño del token: nadie consulta la agenda de otro paciente.
    """
    if int(id_cliente) != request.user.pk:
        return Response(
            {'error': 'No tiene permiso para ver las citas de otro paciente'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.query_params.get('proximas', '').lower() == 'true':
        citas = PmCita.objects.proximas_de_cliente(request.user.pk)
    else:
        citas = PmCita.objects.de_cliente(request.user.pk)

    return Response(PmCitaSerializer(citas, many=True).data)


@api_view(['PATCH'])
@permission_classes([EsCliente])
def cita_cliente_cancelar(request, id_cita):
    """El paciente cancela su propia cita (no la realizará)."""
    entrada = PmCitaClienteCancelarSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)

    # cancelar_por_cliente filtra por (pk, cliente_id), así que una cita ajena
    # devuelve 'no encontrada' en vez de dejarse cancelar.
    cita, error = PmCita.objects.cancelar_por_cliente(
        id_cita, request.user.pk, entrada.validated_data.get('motivo')
    )
    if error:
        return _respuesta_error(error)

    return Response(PmCitaSerializer(cita).data)


@api_view(['PATCH'])
@permission_classes([EsCliente])
def cita_cliente_posponer(request, id_cita):
    """El paciente reprograma su propia cita a una nueva fecha/hora."""
    entrada = PmCitaClientePosponerSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)

    cita, error = PmCita.objects.posponer_por_cliente(
        id_cita,
        request.user.pk,
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
@permission_classes([EsCliente | EsProfesional | EsAdministrador])
def cita_detalle(request, id_cita):
    """
    Retorna el detalle de una cita puntual. Acceso permitido a:
      - el paciente dueño de la cita,
      - el profesional que la atiende, o
      - un administrador.

    Las tres identidades salen del token (ver Security.authentication); antes
    el cliente se identificaba con ?cliente=<id_cliente>, lo que dejaba el
    detalle de cualquier cita al alcance de quien adivinara el id.
    """
    try:
        cita = PmCita.objects.get(pk=id_cita)
    except PmCita.DoesNotExist:
        return Response({'error': 'Cita no encontrada'}, status=status.HTTP_404_NOT_FOUND)

    usuario = request.user
    es_cliente_dueno = isinstance(usuario, PmCliente) and usuario.pk == cita.cliente_id
    es_profesional_dueno = isinstance(usuario, PM_Profesional) and usuario.pk == cita.profesional_id
    es_administrador = isinstance(usuario, Administrador) and usuario.is_staff

    if not (es_cliente_dueno or es_profesional_dueno or es_administrador):
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
