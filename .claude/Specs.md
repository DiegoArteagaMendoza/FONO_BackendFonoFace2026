# Specs para el desarrollo
1. FonoApp y FonoAppPortalMedico son aplicaciónes que integran la arquitectura base de DijangoRest Framework, por lo cual es importante respetarla al 100%, esto considera serializers, querysets, urls, views, models, etc.
2. Se pueden agregar archivos .py dentro de una app siempre que sean acorde a la misma, si son posibles modulos reutilizables deben ir a una carpeta common del proyecto (FonoApp o FonoAppPortalMedico)
3. Siempre que se hagan modelos nuevos se deben realizar las migraciones con los comandos correspondientes (makemigrations y migrate).
4. No se deben enviar respuestas crudas al frontend, tampoco id's de objetos.
5. Deben haber respuestas ante posibles errores (400, 500).