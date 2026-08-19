from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from Security.permissions import EsAdministrador, EsCliente, EsProfesional
from PmMedico.models import PM_Profesional
from PmCita.models import PmCita
from PmVideo.models import PmVideo
from PmVideo.serializer import PmVideoSerializer


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
        serializer.save(cliente=request.user)
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
