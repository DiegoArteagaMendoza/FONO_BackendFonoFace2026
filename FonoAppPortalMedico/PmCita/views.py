from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from Security.permissions import EsAdministrador, EsCliente, EsProfesional
from PmMedico.models import Administrador, PM_Profesional
from PmCliente.models import PmCliente
from PmCita.models import PmCita, PmDisponibilidad
from PmCita.correos import enviar_confirmacion_reserva
from PmCita.serializer import (
    PmCitaSerializer,
    PmCitaReservarBloqueSerializer,
    PmCitaClienteCancelarSerializer,
    PmCitaClientePosponerSerializer,
    PmCitaCancelarSerializer,
    PmCitaPosponerSerializer,
    PmDisponibilidadSerializer,
    PmDisponibilidadPublicaSerializer,
    PmDisponibilidadPublicarSerializer,
    PmCitaSeguimientoSerializer,
    PmCitaSeguimientoCancelarSerializer,
    PmCitaSeguimientoPosponerSerializer,
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
@permission_classes([AllowAny])
def cita_reservar(request):
    """
    Reserva una cita tomando uno de los bloques que el profesional publicó.

    Se puede reservar de dos maneras:

      1. Con sesión de paciente: el dueño de la cita sale del token y el cuerpo
         solo lleva el bloque y el motivo.
      2. Sin sesión: además hay que enviar 'paciente' con los datos personales.
         Con ellos se crea (o se recupera) su ficha; ver
         PmCliente_Queryset.obtener_o_crear_para_reserva.

    Este endpoint es AllowAny a propósito, pero eso NO reabre el problema que
    se corrigió antes: entonces se aceptaba un 'id_cliente' del cuerpo, así que
    conocer el id de alguien bastaba para agendar en su nombre. Ahora no hay
    forma de apuntar a una ficha ajena — solo se pueden enviar datos personales,
    y si el RUT corresponde a una cuenta con contraseña la reserva se rechaza y
    se pide iniciar sesión.
    """
    entrada = PmCitaReservarBloqueSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    datos = entrada.validated_data

    # El token manda: si hay sesión de paciente, los datos personales del cuerpo
    # se ignoran (no tendría sentido reservar para otro estando autenticado).
    if isinstance(request.user, PmCliente):
        cliente = request.user
    else:
        if not datos.get('paciente'):
            return Response(
                {'paciente': ['Debe iniciar sesión o completar sus datos personales para reservar.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            cliente = PmCliente.objects.obtener_o_crear_para_reserva(
                nombres=datos['paciente']['nombres_cliente'],
                apellidos=datos['paciente']['apellidos_clientes'],
                rut=datos['paciente']['rut_cliente'],
                fecha_nacimiento=datos['paciente']['fecha_nacimiento_cliente'],
                email=datos['paciente']['email_cliente'],
                telefono=datos['paciente']['telefono_cliente'],
            )
        except DjangoValidationError as error:
            detalle = error.message_dict if hasattr(error, 'message_dict') else error.messages
            return Response(detalle, status=status.HTTP_400_BAD_REQUEST)

    try:
        cita = PmCita.objects.reservar_bloque(
            cliente=cliente,
            disponibilidad=datos['id_disponibilidad'],
            motivo_consulta=datos.get('motivo_consulta', ''),
        )
    except DjangoValidationError as error:
        detalle = error.message_dict if hasattr(error, 'message_dict') else error.messages
        return Response({'error': detalle}, status=status.HTTP_400_BAD_REQUEST)

    # Confirmación con el código de seguimiento. No corta la reserva si falla:
    # ver enviar_confirmacion_reserva. El código viaja igualmente en la
    # respuesta, así que el frontend puede mostrarlo aunque el correo no salga.
    correo_enviado = enviar_confirmacion_reserva(cita)

    respuesta = PmCitaSerializer(cita).data
    # El frontend necesita saber a qué ficha quedó ligada la cita para poder
    # asociarle después un video, cosa que quien reservó sin sesión no sabría.
    respuesta['reservada_sin_sesion'] = not isinstance(request.user, PmCliente)
    respuesta['codigo_seguimiento'] = cita.codigo_seguimiento
    respuesta['correo_enviado'] = correo_enviado

    return Response(respuesta, status=status.HTTP_201_CREATED)


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


# ==========================================================================
# DISPONIBILIDAD: horas que el profesional publica para ser reservadas
# ==========================================================================

@api_view(['POST'])
@permission_classes([EsProfesional])
def disponibilidad_publicar(request):
    """
    El profesional publica una o varias horas disponibles.

    Cada bloque se evalúa por separado: que una hora choque con algo ya
    publicado no invalida las demás. La respuesta trae las creadas y las
    rechazadas con su motivo, para poder mostrarlo sin adivinar.
    """
    entrada = PmDisponibilidadPublicarSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)
    datos = entrada.validated_data

    creados, rechazados = PmDisponibilidad.objects.publicar_varios(
        profesional=request.user,
        fechas_hora=datos['fechas_hora'],
        duracion_minutos=datos.get('duracion_minutos'),
    )

    codigo = status.HTTP_201_CREATED if creados else status.HTTP_400_BAD_REQUEST
    return Response(
        {
            'creados': PmDisponibilidadSerializer(creados, many=True).data,
            'rechazados': rechazados,
        },
        status=codigo,
    )


@api_view(['GET'])
@permission_classes([EsProfesional])
def disponibilidad_mia(request):
    """
    Horas publicadas por el profesional autenticado, con el dato de si ya
    fueron tomadas. Sin parámetros entrega solo las futuras; con ?todas=true
    incluye también las que ya pasaron.
    """
    if request.query_params.get('todas', '').lower() == 'true':
        bloques = PmDisponibilidad.objects.de_profesional(request.user.pk)
    else:
        bloques = PmDisponibilidad.objects.proximos_de_profesional(request.user.pk)

    return Response(PmDisponibilidadSerializer(bloques, many=True).data)


@api_view(['DELETE'])
@permission_classes([EsProfesional])
def disponibilidad_retirar(request, id_disponibilidad):
    """
    Retira una hora publicada que todavía nadie reservó. Si ya tiene paciente,
    se responde 400 pidiendo que cancele la cita, que sí deja constancia.
    """
    bloque, error = PmDisponibilidad.objects.retirar(id_disponibilidad, request.user.pk)
    if error:
        return _respuesta_error(error, mensaje_404='no encontrado')

    return Response(PmDisponibilidadSerializer(bloque).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def disponibilidad_de_profesional(request, id_profesional):
    """
    Horas libres de un profesional, para que el paciente elija una.

    Es público porque se puede reservar sin haber iniciado sesión, y porque no
    revela nada sensible: solo dice cuándo hay hueco, nunca quién ocupa los
    demás. Se entregan únicamente los bloques reservables (libres y con la
    anticipación mínima por delante).
    """
    bloques = PmDisponibilidad.objects.disponibles_de_profesional(id_profesional)
    return Response(PmDisponibilidadPublicaSerializer(bloques, many=True).data)


# ==========================================================================
# SEGUIMIENTO POR CÓDIGO
# --------------------------------------------------------------------------
# Quien reservó sin cuenta no tiene sesión con la que identificarse, así que el
# código que recibió por correo hace de credencial. De ahí que estos endpoints
# sean públicos: el código ES la autorización.
#
# Por eso importa que sea impredecible (ver generar_codigo_seguimiento, que usa
# secrets sobre un alfabeto de 31 símbolos) y que la respuesta no exponga ids
# internos ni datos que no sean de esa cita.
#
# Pendiente para producción: limitar los intentos por IP. Sin eso, nada impide
# probar códigos en masa, aunque el espacio de búsqueda lo haga poco práctico.
# ==========================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def cita_seguimiento(request, codigo):
    """Detalle de una cita a partir de su código de seguimiento."""
    cita = PmCita.objects.por_codigo(codigo)
    if not cita:
        return Response(
            {'error': 'No encontramos ninguna hora con ese código. Revísalo e inténtalo de nuevo.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(PmCitaSeguimientoSerializer(cita).data)


@api_view(['PATCH'])
@permission_classes([AllowAny])
def cita_seguimiento_cancelar(request, codigo):
    """Cancela la cita desde el seguimiento (cuenta como cancelación del paciente)."""
    entrada = PmCitaSeguimientoCancelarSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)

    cita, error = PmCita.objects.cancelar_por_codigo(codigo, entrada.validated_data.get('motivo'))
    if error:
        return _respuesta_error(error)

    return Response(PmCitaSeguimientoSerializer(cita).data)


@api_view(['PATCH'])
@permission_classes([AllowAny])
def cita_seguimiento_posponer(request, codigo):
    """Reprograma la cita desde el seguimiento."""
    entrada = PmCitaSeguimientoPosponerSerializer(data=request.data)
    entrada.is_valid(raise_exception=True)

    cita, error = PmCita.objects.posponer_por_codigo(
        codigo,
        entrada.validated_data['fecha_hora'],
        entrada.validated_data.get('motivo'),
    )
    if error:
        return _respuesta_error(error)

    return Response(PmCitaSeguimientoSerializer(cita).data)
