# **DOCUMENTACION API FONO**

## INFORMACION (endpoint base: api/informacion/)

### 1. Listar GET

* Endpoint: `listar/`
* Acceso: Público
* Variable `categoria` (opcional) con valores SA, CU, NU, TI, ejemplo `/listar/?categoria=SA`
* Ejemplo de salida esperada (Status 200):

```json
[
    {
        "id_informacion": 1,
        "titulo": "Síntomas de parvovirus en cachorros",
        "categoria": "SA",
        "categoria_display": "Salud Animal",
        "contenido": "El parvovirus es una enfermedad muy contagiosa que afecta principalmente...",
        "fecha_creacion": "2026-06-15T10:30:00Z",
        "fecha_actualizacion": "2026-06-15T10:30:00Z",
        "estado": true,
        "FonoApp_Administracion": 2, 
        "imagenes": [
            {
                "id": 1,
                "imagen": "http://tu-dominio.com/media/informacion/imagenes/perrito_enfermo.jpg",
                "fecha_subida": "2026-06-15T10:30:05Z"
            },
            {
                "id": 2,
                "imagen": "http://tu-dominio.com/media/informacion/imagenes/sintomas.jpg",
                "fecha_subida": "2026-06-15T10:30:10Z"
            }
        ]
    },
    {
        "id_informacion": 2,
        "titulo": "Beneficios de la dieta BARF",
        "categoria": "NU",
        "categoria_display": "Nutrición",
        "contenido": "La alimentación cruda biológicamente adecuada aporta grandes beneficios...",
        "fecha_creacion": "2026-06-14T15:20:00Z",
        "fecha_actualizacion": "2026-06-14T16:00:00Z",
        "estado": true,
        "FonoApp_Administracion": 1,
        "imagenes": [] 
    }
]

```

### 2. Crear POST

* Endpoint: `crear/`
* Acceso: Requiere validación Bearer (Token JWT)
* Formato de envío: `FormData` (multipart/form-data) obligatorio por el manejo de imágenes.
* Ejemplo de entrada esperada (Frontend / JS):

```javascript
const formData = new FormData();
formData.append('titulo', 'Vacunas recomendadas para perros');
formData.append('categoria', 'SA');
formData.append('contenido', 'Las vacunas esenciales son la séxtuple y la antirrábica...');
// Las imágenes son opcionales (máximo 4)
formData.append('imagenes_subidas', archivoImagen1); 

```

* Ejemplo de salida esperada (Status 201):

```json
{
    "id_informacion": 3,
    "titulo": "Vacunas recomendadas para perros",
    "categoria": "SA",
    "categoria_display": "Salud Animal",
    "contenido": "Las vacunas esenciales son la séxtuple y la antirrábica...",
    "fecha_creacion": "2026-06-15T12:00:00Z",
    "fecha_actualizacion": "2026-06-15T12:00:00Z",
    "estado": true,
    "FonoApp_Administracion": 1,
    "imagenes": [
        {
            "id": 5,
            "imagen": "http://tu-dominio.com/media/informacion/imagenes/vacuna1.jpg",
            "fecha_subida": "2026-06-15T12:00:02Z"
        }
    ]
}

```

### 3. Editar PATCH / PUT

* Endpoint: `<id_informacion>/editar/` (Ejemplo: `1/editar/`)
* Acceso: Requiere validación Bearer (Token JWT)
* Formato de envío: `JSON` (Este endpoint actualiza solo campos de texto de forma parcial).
* Ejemplo de entrada esperada (JSON):

```json
{
    "titulo": "Título corregido y actualizado",
    "categoria": "CU"
}

```

* Ejemplo de salida esperada (Status 200):

```json
{
    "id_informacion": 1,
    "titulo": "Título corregido y actualizado",
    "categoria": "CU",
    "categoria_display": "Cuidados Básicos",
    "contenido": "El parvovirus es una enfermedad muy contagiosa que afecta principalmente...",
    "fecha_creacion": "2026-06-15T10:30:00Z",
    "fecha_actualizacion": "2026-06-16T09:15:00Z",
    "estado": true,
    "FonoApp_Administracion": 2, 
    "imagenes": [
        {
            "id": 1,
            "imagen": "http://tu-dominio.com/media/informacion/imagenes/perrito_enfermo.jpg",
            "fecha_subida": "2026-06-15T10:30:05Z"
        }
    ]
}

```

### 4. Eliminar DELETE

* Endpoint: `<id_informacion>/eliminar/` (Ejemplo: `1/eliminar/`)
* Acceso: Requiere validación Bearer (Token JWT)
* Formato de envío: Ninguno (solo se envía la petición HTTP DELETE).
* Nota: Realiza un borrado lógico (cambia el atributo `estado` a `false` ocultándolo de la vista pública).
* Ejemplo de salida esperada (Status 200):

```json
{
    "mensaje": "Información eliminada correctamente"
}

```