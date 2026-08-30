from rest_framework.decorators import (
    api_view,
    permission_classes,
    parser_classes,
    throttle_classes,
)
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework import status

# Error base de Cloudinary: cubre BadRequest (archivo ilegible) y también los
# fallos de red o de cuota, que tampoco deben salir como un 500 sin explicación.
from cloudinary.exceptions import Error as CloudinaryError

from Security.permissions import EsAdministrador, EsCliente, EsProfesional
from PmMedico.models import PM_Profesional
from PmCita.models import PmCita
from PmVideo.models import PmVideo
from PmVideo.serializer import PmVideoSerializer, PmVideoSeguimientoSerializer


def _guardar_video(serializer, **campos):
    """
    Guarda el video traduciendo el rechazo del proveedor en un 400.

    El archivo no pasa por el almacenamiento de Django: CloudinaryField lo sube
    con su propio SDK dentro de save(), y si Cloudinary lo rechaza —un .mp4 que
    en realidad no es un video, un archivo truncado— lanza una excepción que sin
    esto sale como error 500 y una página de Django en la cara del paciente.
    El serializer valida extensión, peso y duración, pero no puede saber si el
    contenido es realmente reproducible: eso solo lo dice el proveedor.

    Devuelve la respuesta de error, o None si guardó bien.
    """
    try:
        serializer.save(**campos)
        return None
    except CloudinaryError:
        return Response(
            {'video': 'No pudimos procesar el archivo. Asegúrate de que sea un video que se '
                      'reproduzca correctamente e inténtalo de nuevo.'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class SubidaPorCodigoThrottle(AnonRateThrottle):
    """
    Límite para la subida con código de seguimiento.

    Es el único endpoint anónimo que acepta archivos de hasta 50 MB, así que sin
    tope basta con un código válido para llenar el almacenamiento a base de
    reintentos. El ritmo lo define PM_VIDEO_SUBIDA_POR_CODIGO en settings.
    """
    scope = 'pm_video_subida_codigo'


# ==========================================================================
# SUBIDA Y CONSULTA DEL PROPIO VIDEO (lo hace el paciente)
# --------------------------------------------------------------------------
# El paciente debe estar autenticado y el dueño del video se toma del token,
# nunca del cuerpo de la petición: así nadie puede subir material clínico a
# nombre de otra persona ni ver videos ajenos.
# ==========================================================================

@api_view(['POST'])
@permission_classes([EsCliente])
@parser_classes([MultiPartParser, FormParser])
def video_subir(request):
    """
    Recibe el video de síntomas del paciente autenticado (multipart/form-data).
    La fecha de expiración se calcula sola: 30 días desde la subida.
    """
    # El paciente va por contexto para que el serializer pueda comprobar que la
    # cita indicada (si viene) es realmente suya.
    serializer = PmVideoSerializer(data=request.data, context={'cliente': request.user})

    if serializer.is_valid():
        # El dueño sale del token, ignorando cualquier 'cliente' que venga en el body
        error = _guardar_video(serializer, cliente=request.user)
        if error:
            return error
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([EsCliente])
def mis_videos(request):
    """Videos vigentes del paciente autenticado."""
    videos = PmVideo.objects.del_cliente(request.user.pk)
    return Response(PmVideoSerializer(videos, many=True).data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([EsCliente])
def mi_video_eliminar(request, id_video):
    """
    El paciente retira un video propio antes de que venza.
    Solo puede borrar los suyos: se comprueba contra el id del token.
    """
    video = PmVideo.objects.vigentes().filter(id_video=id_video, cliente_id=request.user.pk).first()

    if not video:
        return Response(
            {'error': 'El video no existe, no es tuyo o ya fue eliminado'},
            status=status.HTTP_404_NOT_FOUND
        )

    PmVideo.objects.eliminar(id_video, PmVideo.MotivoEliminacion.RETIRO_PACIENTE)
    return Response({'mensaje': 'Video eliminado correctamente'}, status=status.HTTP_200_OK)


# ==========================================================================
# CONSULTA Y ELIMINACIÓN (lado del profesional)
# --------------------------------------------------------------------------
# Exponen material clínico del paciente, por eso usan los roles definidos en
# Security/permissions.py: el profesional que revisa los síntomas o un
# administrador del sistema.
# ==========================================================================

@api_view(['GET'])
@permission_classes([EsProfesional | EsAdministrador])
def videos_listar(request):
    """
    Lista los videos vigentes. Se puede filtrar por cliente (?cliente=1) o
    por cita (?cita=5). Los videos vencidos nunca se entregan, aunque el
    archivo aún no se haya purgado.

    Cuando se filtra por cita y quien consulta es un profesional (no un
    administrador), solo se entrega si la cita es suya: evita que un
    profesional vea el video de una cita ajena.
    """
    id_cliente = request.query_params.get('cliente', None)
    id_cita = request.query_params.get('cita', None)

    if id_cita:
        if isinstance(request.user, PM_Profesional):
            if not PmCita.objects.filter(pk=id_cita, profesional_id=request.user.pk).exists():
                return Response(
                    {'error': 'No tiene permiso para ver los videos de esa cita'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        videos = PmVideo.objects.de_cita(id_cita)
    elif id_cliente:
        videos = PmVideo.objects.del_cliente(id_cliente)
    else:
        videos = PmVideo.objects.vigentes()

    serializer = PmVideoSerializer(videos, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([EsProfesional | EsAdministrador])
def video_detalle(request, id_video):
    """Retorna un video puntual, solo si sigue vigente."""
    video = PmVideo.objects.vigentes().filter(id_video=id_video).first()

    if not video:
        return Response(
            {'error': 'El video no existe, fue eliminado o ya cumplió sus 30 días'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = PmVideoSerializer(video)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([EsProfesional | EsAdministrador])
def video_eliminar(request, id_video):
    """
    Elimina el video por orden del médico: borra el archivo del disco y deja
    el registro marcado con el motivo para trazabilidad.
    """
    eliminado = PmVideo.objects.eliminar(id_video, PmVideo.MotivoEliminacion.ORDEN_MEDICA)

    if eliminado:
        return Response(
            {'mensaje': 'Video eliminado correctamente por orden médica'},
            status=status.HTTP_200_OK
        )

    return Response(
        {'error': 'El video no existe o ya estaba eliminado'},
        status=status.HTTP_404_NOT_FOUND
    )


# ==========================================================================
# VIDEO DE QUIEN RESERVÓ SIN CUENTA (seguimiento por código)
# --------------------------------------------------------------------------
# Quien pidió hora sin registrarse no tiene sesión con la que identificarse:
# su credencial es el código que le llegó por correo. Estos tres endpoints le
# dan sobre SU cita lo mismo que el paciente con cuenta tiene sobre las suyas
# —ver, adjuntar y retirar el video— sin abrir nada más.
#
# El código acota el alcance por completo: la cita sale de él, el dueño sale de
# la cita, y nada de eso se acepta desde el cuerpo de la petición. Por eso
# tampoco se devuelve ningún id (regla 4 del Specs): el video se identifica por
# su cita, que ya viene dada por el código.
# ==========================================================================

def _cita_del_codigo(codigo):
    """
    Resuelve la cita del código y comprueba que admita video.

    Devuelve (cita, respuesta_de_error). Si la cita sirve, el segundo elemento
    es None; si no, trae ya armada la respuesta que debe devolver la vista.
    """
    cita = PmCita.objects.por_codigo(codigo)

    if not cita:
        return None, Response(
            {'error': 'No encontramos ninguna hora con ese código. Revísalo e inténtalo de nuevo.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not cita.permite_carga_video:
        return None, Response(
            {'error': 'Esta hora no admite adjuntar un video.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return cita, None


@api_view(['GET'])
@permission_classes([AllowAny])
def video_seguimiento_listar(request, codigo):
    """El video que ya está adjunto a la hora de ese código, si es que hay."""
    cita, error = _cita_del_codigo(codigo)
    if error:
        return error

    videos = PmVideo.objects.de_cita(cita.pk)
    return Response(
        PmVideoSeguimientoSerializer(videos, many=True).data,
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
@throttle_classes([SubidaPorCodigoThrottle])
def video_seguimiento_subir(request, codigo):
    """
    Adjunta un video a la hora de ese código.

    Se admite uno solo por hora: si ya hay uno vigente hay que retirarlo antes.
    Sin ese límite, el código serviría para llenar el almacenamiento de la cita
    subiendo archivos de 50 MB uno tras otro.
    """
    cita, error = _cita_del_codigo(codigo)
    if error:
        return error

    if not cita.esta_activa:
        return Response(
            {'error': 'Solo se puede adjuntar un video a una hora reservada (no cancelada ni realizada).'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if PmVideo.objects.de_cita(cita.pk).exists():
        return Response(
            {'error': 'Esta hora ya tiene un video adjunto. Retíralo si quieres subir otro.'},
            status=status.HTTP_409_CONFLICT,
        )

    # La cita y el dueño van por contexto, nunca desde el cuerpo: el código es
    # lo único que decide a qué hora y a nombre de quién se sube.
    serializer = PmVideoSeguimientoSerializer(
        data=request.data,
        context={'cita': cita, 'cliente': cita.cliente},
    )

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    error = _guardar_video(serializer, cliente=cita.cliente, cita=cita)
    if error:
        return error

    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def video_seguimiento_eliminar(request, codigo):
    """
    Retira el video adjunto a la hora de ese código.

    No recibe el id del video: la cita ya lo determina, y así el endpoint no
    sirve para borrar material de otra ficha probando números.
    """
    cita, error = _cita_del_codigo(codigo)
    if error:
        return error

    videos = list(PmVideo.objects.de_cita(cita.pk))

    if not videos:
        return Response(
            {'error': 'Esta hora no tiene ningún video adjunto.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Con cuenta se pueden colgar varios videos de una misma hora; desde el
    # código no se sabe cuál de ellos se quiere retirar, y borrarlos todos sería
    # destruir más de lo pedido. En ese caso se deriva a la sesión del paciente.
    if len(videos) > 1:
        return Response(
            {'error': 'Esta hora tiene más de un video. Entra con tu cuenta para elegir cuál retirar.'},
            status=status.HTTP_409_CONFLICT,
        )

    PmVideo.objects.eliminar(videos[0].pk, PmVideo.MotivoEliminacion.RETIRO_PACIENTE)
    return Response({'mensaje': 'Video retirado correctamente'}, status=status.HTTP_200_OK)
