# **DOCUMENTACION API FONO**

## CUIDADOS (endpoint base: api/cuidados/)

### 1. Listar GET
- **Endpoint:** `listar/`
- **Acceso:** Público
- **Ejemplo de salida esperada (Status 200 OK):**
```json
[
    {
        "id_cuidado": 1,
        "publico": "PUBLICO_GENERAL",
        "publico_display": "Público General",
        "titulo": "Hidratación constante",
        "contenido": "Es fundamental beber al menos 2 litros de agua diarios para mantener las cuerdas vocales lubricadas...",
        "img": "http://tu-dominio.com/media/cuidados/imagenes/agua.jpg",
        "fuente": "https://www.nidcd.nih.gov/es/salud/cuidado-de-la-voz",
        "estado": true,
        "FonoApp_Administracion": 1
    },
    {
        "id_cuidado": 2,
        "publico": "CANTANTES_ACTORES",
        "publico_display": "Cantantes y/o Actores",
        "titulo": "Calentamiento antes de funciones",
        "contenido": "Realizar ejercicios de tracto vocal semiocluido (TVSO) durante 15 minutos previos...",
        "img": null,
        "fuente": null,
        "estado": true,
        "FonoApp_Administracion": 2
    }
]
```

### 2. Filtrar por Público GET
- **Endpoint:** `publico/<tipo_publico>/` (Ejemplo: `publico/PROFESORES/`)
- **Acceso:** Público
- **Variable `<tipo_publico>` (Obligatoria en la URL):** Filtra los cuidados según el segmento objetivo. Valores permitidos: `NIÑOS`, `PROFESORES`, `CANTANTES_ACTORES`, `LOCUTORES`, `PUBLICO_GENERAL`.
- **Ejemplo de salida esperada (Status 200 OK):**
```json
[
    {
        "id_cuidado": 3,
        "publico": "PROFESORES",
        "publico_display": "Profesores",
        "titulo": "Uso de micrófonos en el aula",
        "contenido": "El uso de amplificadores de voz reduce el estrés de las cuerdas vocales en ambientes ruidosos...",
        "img": "http://tu-dominio.com/media/cuidados/imagenes/microfono.jpg",
        "fuente": "https://ejemplo.com/estudio-docentes",
        "estado": true,
        "FonoApp_Administracion": 1
    }
]
```

### 3. Crear POST
- **Endpoint:** `crear/`
- **Acceso:** Requiere validación Bearer (Token JWT)
- **Formato de envío:** `FormData` (`multipart/form-data`) obligatorio si se envía imagen, o `JSON` si solo se envía texto.
- **Ejemplo de entrada esperada (Frontend / JS con FormData):**
```javascript
const formData = new FormData();
formData.append('titulo', 'Descanso vocal');
formData.append('publico', 'LOCUTORES');
formData.append('contenido', 'Tomar pausas de silencio absoluto de 10 minutos cada hora de locución continua.');
formData.append('fuente', 'https://ejemplo.com/salud-vocal');
// La imagen es opcional
formData.append('img', archivoImagen); 
```
- **Ejemplo de salida esperada (Status 201 Created):**
```json
{
    "id_cuidado": 4,
    "publico": "LOCUTORES",
    "publico_display": "Locutores",
    "titulo": "Descanso vocal",
    "contenido": "Tomar pausas de silencio absoluto de 10 minutos cada hora de locución continua.",
    "img": "http://tu-dominio.com/media/cuidados/imagenes/descanso.jpg",
    "fuente": "https://ejemplo.com/salud-vocal",
    "estado": true,
    "FonoApp_Administracion": 1
}
```

### 4. Editar PATCH / PUT
- **Endpoint:** `<id_cuidado>/editar/` (Ejemplo: `1/editar/`)
- **Acceso:** Requiere validación Bearer (Token JWT)
- **Formato de envío:** `JSON` (`application/json`) para actualizar textos, o `FormData` si se actualiza la imagen. Se pueden enviar actualizaciones parciales.
- **Ejemplo de entrada esperada (JSON):**
```json
{
    "titulo": "Hidratación constante y alimentación",
    "publico": "PUBLICO_GENERAL"
}
```
- **Ejemplo de salida esperada (Status 200 OK):**
```json
{
    "mensaje": "Cuidado actualizado correctamente"
}
```

### 5. Eliminar DELETE
- **Endpoint:** `<id_cuidado>/eliminar/` (Ejemplo: `1/eliminar/`)
- **Acceso:** Requiere validación Bearer (Token JWT)
- **Formato de envío:** Ninguno (el ID va en la URL).
- **Nota:** Realiza un borrado lógico, cambiando la propiedad `estado` a `False`.
- **Ejemplo de salida esperada (Status 200 OK):**
```json
{
    "mensaje": "Cuidado eliminado correctamente"
}
```