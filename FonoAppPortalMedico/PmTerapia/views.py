from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from Security.permissions import EsProfesional, EsCliente
from Security.archivos import guardar_o_400, borrar_de_cloudinary
from PmCita.models import PmCita
from PmTerapia.models import PmEjercicio, PmPlanTerapia, PmVideoProgreso
from PmTerapia.serializer import (
    PmEjercicioSerializer,
    PmEjercicioEditarSerializer,
    PmPlanTerapiaSerializer,
    PmPlanTerapiaEntradaSerializer,
    PmVideoProgresoSerializer,
    PmVideoProgresoSubirSerializer,
    PmPlanTerapiaSeguimientoSerializer,
    PmRetroalimentacionSerializer,
)


# ==========================================================================
# CATÁLOGO DE EJERCICIOS (lo administra el fonoaudiólogo)
# --------------------------------------------------------------------------
# Los ejercicios son privados de cada profesional. El dueño sale siempre del
# token, nunca del cuerpo, y toda consulta pasa por 'de_profesional': no hay
# forma de listar, editar ni borrar el ejercicio de otro. Cuando uno no es
# propio se responde 404, no 403, para no confirmar que existe.
# ==========================================================================

def _no_encontrado():
    return Response(
        {'error': 'El ejercicio no existe o no está en tu catálogo.'},
        status=status.HTTP_404_NOT_FOUND,
    )


@api_view(['GET'])
@permission_classes([EsProfesional])
def ejercicios_listar(request):
    """Catálogo vigente del fonoaudiólogo autenticado."""
    ejercicios = PmEjercicio.objects.de_profesional(request.user.pk)
    return Response(PmEjercicioSerializer(ejercicios, many=True).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([EsProfesional])
@parser_classes([MultiPartParser, FormParser])
def ejercicio_crear(request):
    """
    Crea un ejercicio con su video de ejemplo (multipart/form-data).
    El video es obligatorio: un ejercicio sin demostración no le sirve al paciente.
    """
    serializer = PmEjercicioSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # El dueño sale del token, ignorando cualquier 'profesional' del body.
    error = guardar_o_400(serializer, profesional=request.user)
    if error:
        return error

    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([EsProfesional])
@parser_classes([MultiPartParser, FormParser])
def ejercicio_editar(request, id_ejercicio):
    """
    Edita nombre, instrucciones o el video de ejemplo.

    Si llega un video nuevo, el anterior se borra de Cloudinary DESPUÉS de que
    el nuevo quedó guardado: si la subida falla, el ejercicio conserva el que
    tenía en vez de quedarse sin ninguno.
    """
    ejercicio = PmEjercicio.objects.propio(id_ejercicio, request.user.pk)
    if not ejercicio:
        return _no_encontrado()

    video_anterior = ejercicio.video_ejemplo if 'video_ejemplo' in request.data else None

    serializer = PmEjercicioEditarSerializer(ejercicio, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    error = guardar_o_400(serializer)
    if error:
        return error

    if video_anterior:
        borrar_de_cloudinary(video_anterior)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([EsProfesional])
def ejercicio_eliminar(request, id_ejercicio):
    """
    Saca el ejercicio del catálogo (borrado lógico).

    Si algún plan de terapia lo tiene asignado, el video de ejemplo se conserva
    para que ese paciente lo siga viendo; si no, se borra de Cloudinary.
    """
    ejercicio = PmEjercicio.objects.propio(id_ejercicio, request.user.pk)
    if not ejercicio:
        return _no_encontrado()

    PmEjercicio.objects.eliminar(ejercicio)
    return Response({'mensaje': 'Ejercicio eliminado del catálogo'}, status=status.HTTP_200_OK)


# ==========================================================================
# PLAN DE TERAPIA (lado del fonoaudiólogo)
# --------------------------------------------------------------------------
# Un plan se crea desde una cita realizada y pertenece al par paciente–fono.
# Todo lo que cambia datos pasa por el queryset, que devuelve (plan, error);
# aquí solo se traduce a una respuesta. Un plan ajeno responde 404, no 403.
# ==========================================================================

def _plan_no_encontrado():
    return Response({'error': 'El plan no existe o no es tuyo.'}, status=status.HTTP_404_NOT_FOUND)


def _error_400(texto):
    return Response({'error': texto}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([EsProfesional])
def plan_crear(request):
    """
    Crea el plan de un paciente a partir de una cita realizada.
    Cuerpo: id_cita, periodicidad, indicaciones (opcional), ejercicios (1 a 3).
    """
    entrada = PmPlanTerapiaEntradaSerializer(data=request.data, context={'profesional': request.user})
    if not entrada.is_valid():
        return Response(entrada.errors, status=status.HTTP_400_BAD_REQUEST)

    datos = entrada.validated_data
    faltan = [campo for campo in ('id_cita', 'periodicidad', 'ejercicios') if campo not in datos]
    if faltan:
        return _error_400(f'Faltan datos: {", ".join(faltan)}.')

    cita = PmCita.objects.select_related('cliente').filter(pk=datos['id_cita']).first()
    if not cita:
        return Response({'error': 'La cita no existe.'}, status=status.HTTP_404_NOT_FOUND)

    plan, error = PmPlanTerapia.objects.crear(
        profesional=request.user,
        cita=cita,
        ejercicios=datos['ejercicios'],
        periodicidad=datos['periodicidad'],
        indicaciones=datos.get('indicaciones', ''),
    )
    if error:
        return _error_400(error)

    return Response(PmPlanTerapiaSerializer(plan).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([EsProfesional])
def planes_listar(request):
    """
    Los planes del fonoaudiólogo. Por defecto solo los activos; con
    ?todos=true incluye los cerrados.
    """
    planes = PmPlanTerapia.objects.de_profesional(request.user.pk)
    if request.query_params.get('todos') != 'true':
        planes = planes.activos()
    return Response(PmPlanTerapiaSerializer(planes, many=True).data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([EsProfesional])
def plan_detalle(request, id_plan):
    plan = PmPlanTerapia.objects.propio_de_profesional(id_plan, request.user.pk)
    if not plan:
        return _plan_no_encontrado()
    return Response(PmPlanTerapiaSerializer(plan).data, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([EsProfesional])
def plan_ajustar(request, id_plan):
    """
    Cambia ejercicios, periodicidad o indicaciones. Todos opcionales; lo que
    no viene se deja como está. Cambiar la periodicidad reinicia el plan a hoy.
    """
    plan = PmPlanTerapia.objects.propio_de_profesional(id_plan, request.user.pk)
    if not plan:
        return _plan_no_encontrado()

    entrada = PmPlanTerapiaEntradaSerializer(data=request.data, context={'profesional': request.user})
    if not entrada.is_valid():
        return Response(entrada.errors, status=status.HTTP_400_BAD_REQUEST)

    datos = entrada.validated_data
    plan, error = PmPlanTerapia.objects.ajustar(
        plan,
        ejercicios=datos.get('ejercicios'),
        periodicidad=datos.get('periodicidad'),
        indicaciones=datos.get('indicaciones'),
    )
    if error:
        return _error_400(error)

    return Response(PmPlanTerapiaSerializer(plan).data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([EsProfesional])
def plan_cerrar(request, id_plan):
    plan = PmPlanTerapia.objects.propio_de_profesional(id_plan, request.user.pk)
    if not plan:
        return _plan_no_encontrado()

    plan, error = PmPlanTerapia.objects.cerrar(plan)
    if error:
        return _error_400(error)

    return Response(PmPlanTerapiaSerializer(plan).data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([EsProfesional])
def plan_de_cita(request, id_cita):
    """
    El plan activo del paciente de esa cita con este fonoaudiólogo, si lo hay.
    La agenda lo usa para decidir si ofrece "Asignar plan" o "Ajustar plan".

    Responde siempre { "plan": ... }: con el plan, o con null cuando no hay.
    No es un error, es la respuesta. Acompaña el nombre del paciente y si tiene
    cuenta, para que el formulario pueda explicar por qué no se podrá asignar
    antes de que el fonoaudiólogo llene todo. (Un Response(None) suelto no manda 'null':
    DRF lo convierte en un cuerpo vacío sin Content-Type y el cliente no puede
    parsearlo.)
    """
    cita = PmCita.objects.select_related('cliente').filter(pk=id_cita, profesional_id=request.user.pk).first()
    if not cita:
        return Response({'error': 'La cita no existe o no es tuya.'}, status=status.HTTP_404_NOT_FOUND)

    plan = PmPlanTerapia.objects.activo_del_par(cita.cliente_id, request.user.pk)
    return Response(
        {
            'plan': PmPlanTerapiaSerializer(plan).data if plan else None,
            # Cuando no hay plan, el formulario igual necesita saber a quién se
            # lo va a asignar y si podrá (sin cuenta, el backend lo rechaza).
            'paciente_nombre': f'{cita.cliente.nombres_cliente} {cita.cliente.apellidos_clientes}',
            'paciente_tiene_cuenta': bool(cita.cliente.password_cliente),
            'cita_realizada': cita.estado == PmCita.Estado.REALIZADA,
        },
        status=status.HTTP_200_OK,
    )


# ==========================================================================
# PLAN DE TERAPIA (lado del paciente)
# --------------------------------------------------------------------------
# Solo lectura en esta entrega: sus planes activos con los ejercicios, el
# video de ejemplo y el periodo actual. La subida de videos llega después.
# ==========================================================================

@api_view(['GET'])
@permission_classes([EsCliente])
def mis_planes(request):
    planes = PmPlanTerapia.objects.de_cliente(request.user.pk).activos()
    return Response(PmPlanTerapiaSerializer(planes, many=True).data, status=status.HTTP_200_OK)


# ==========================================================================
# VIDEOS DE PROGRESO (lado del paciente)
# --------------------------------------------------------------------------
# El paciente sube un video por ejercicio en cada periodo, ve su historial con
# la retroalimentación y puede retirar uno propio. El dueño sale del token y el
# plan se comprueba como suyo; el periodo lo calcula el servidor en hora de
# Chile: nada de eso se acepta desde el cuerpo.
# ==========================================================================

def _mi_plan_o_404(request, id_plan):
    plan = PmPlanTerapia.objects.propio_de_cliente(id_plan, request.user.pk)
    if not plan:
        return None, Response({'error': 'El plan no existe o no es tuyo.'}, status=status.HTTP_404_NOT_FOUND)
    return plan, None


@api_view(['POST'])
@permission_classes([EsCliente])
@parser_classes([MultiPartParser, FormParser])
def mi_plan_video_subir(request, id_plan):
    """
    Sube un video de progreso (multipart/form-data): id_plan_ejercicio, video,
    duracion_segundos y comentario opcional. Vive 7 días.
    """
    plan, error = _mi_plan_o_404(request, id_plan)
    if error:
        return error

    entrada = PmVideoProgresoSubirSerializer(data=request.data)
    if not entrada.is_valid():
        return Response(entrada.errors, status=status.HTTP_400_BAD_REQUEST)
    datos = entrada.validated_data

    asignacion, periodo, error = PmVideoProgreso.objects.preparar_subida(plan, datos['id_plan_ejercicio'])
    if error:
        return _error_400(error)

    video = PmVideoProgreso(
        plan_ejercicio=asignacion,
        video=datos['video'],
        duracion_segundos=datos['duracion_segundos'],
        comentario=datos.get('comentario', ''),
        numero_periodo=periodo,
    )

    # El archivo se sube dentro de save(); si Cloudinary lo rechaza, 400.
    error = guardar_o_400(video)
    if error:
        return error

    return Response(PmVideoProgresoSerializer(video).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([EsCliente])
def mi_plan_videos(request, id_plan):
    """Historial del plan: vigentes y vencidos, del más nuevo al más viejo."""
    plan, error = _mi_plan_o_404(request, id_plan)
    if error:
        return error

    videos = PmVideoProgreso.objects.de_plan(plan.pk)
    return Response(PmVideoProgresoSerializer(videos, many=True).data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([EsCliente])
def mi_video_progreso_eliminar(request, id_video):
    """Retira un video propio que aún esté vigente."""
    video = PmVideoProgreso.objects.propio_de_cliente(id_video, request.user.pk)
    if not video:
        return Response(
            {'error': 'El video no existe, no es tuyo o ya no está disponible.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    PmVideoProgreso.objects.eliminar(video, PmVideoProgreso.MotivoEliminacion.RETIRO_PACIENTE)
    return Response({'mensaje': 'Video retirado correctamente'}, status=status.HTTP_200_OK)


# ==========================================================================
# SEGUIMIENTO (lado del fonoaudiólogo)
# --------------------------------------------------------------------------
# El detalle con los periodos cumplidos, el historial de videos del plan y la
# retroalimentación escrita. Solo sobre planes propios; lo ajeno es 404.
# ==========================================================================

@api_view(['GET'])
@permission_classes([EsProfesional])
def plan_seguimiento(request, id_plan):
    """El plan con sus periodos cerrados y qué ejercicios faltaron en cada uno."""
    plan = PmPlanTerapia.objects.propio_de_profesional(id_plan, request.user.pk)
    if not plan:
        return _plan_no_encontrado()
    return Response(PmPlanTerapiaSeguimientoSerializer(plan).data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([EsProfesional])
def plan_videos(request, id_plan):
    """Historial del plan, del más nuevo al más viejo, vigentes y vencidos."""
    plan = PmPlanTerapia.objects.propio_de_profesional(id_plan, request.user.pk)
    if not plan:
        return _plan_no_encontrado()

    videos = PmVideoProgreso.objects.de_plan(plan.pk)
    return Response(PmVideoProgresoSerializer(videos, many=True).data, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([EsProfesional])
def video_retroalimentar(request, id_video):
    """
    Escribe o corrige la retroalimentación de un video. Con texto vacío se
    borra. Funciona también sobre videos vencidos: el archivo ya no está, pero
    el paciente sigue leyendo el comentario.
    """
    video = (PmVideoProgreso.objects
             .filter(pk=id_video, plan_ejercicio__plan__profesional_id=request.user.pk)
             .select_related('plan_ejercicio__ejercicio')
             .first())
    if not video:
        return Response({'error': 'El video no existe o no es de un plan tuyo.'}, status=status.HTTP_404_NOT_FOUND)

    entrada = PmRetroalimentacionSerializer(data=request.data)
    if not entrada.is_valid():
        return Response(entrada.errors, status=status.HTTP_400_BAD_REQUEST)

    texto = entrada.validated_data['retroalimentacion'].strip()
    video.retroalimentacion = texto or None
    video.fecha_retroalimentacion = timezone.now() if texto else None
    video.save(update_fields=['retroalimentacion', 'fecha_retroalimentacion'])

    return Response(PmVideoProgresoSerializer(video).data, status=status.HTTP_200_OK)
