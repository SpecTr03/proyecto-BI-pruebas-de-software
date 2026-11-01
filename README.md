# proyecto-BI-pruebas-de-software
Proyecto final de pruebas de software que tiene como objetivo crear un proceso ETL para posteriormente presentar los resultados en un dashboard, facilitando la toma de decisiones.

## Stack tecnológico previsto

- Metodología de ciencia de datos: **CRISP-DM**.
- Base de datos: **MongoDB** como opción principal NoSQL. Apache Cassandra queda como alternativa para escenarios distribuidos de Big Data.
- Procesamiento y analítica: **Python**, pandas, NumPy, scikit-learn, XGBoost y LightGBM.
- Backend: **Python con FastAPI**.
- Frontend: **JavaScript/TypeScript, React y Vite**.
- Visualización: **Plotly, Chart.js o D3.js**.

## Configuración local

Se recomienda ejecutar Python dentro de un entorno virtual aislado.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r scripts/requirements.txt
python -m pip install -r notebooks/requirements.txt
python -m ipykernel install --user --name proyecto-bi --display-name "Proyecto BI"
```

Para abrir un terminal nuevo sin activar el entorno, los ejecutables se encuentran en:

```text
.venv\Scripts\python.exe
.venv\Scripts\jupyter.exe
```

## Estructura

```text
data/       Dataset fuente y datos procesados
notebooks/  Análisis exploratorio y prototipado
scripts/    ETL y carga hacia NoSQL
docs/       Documentación e imágenes
```

## Ejecutar el notebook

```powershell
.\.venv\Scripts\Activate.ps1
jupyter lab notebooks/resultados-saber-pro-analisis.ipynb
```

Seleccione el kernel `Proyecto BI`. La ruta al CSV desde el notebook es `../data/Resultados_Saber_Pro_20260927.csv`.

## Ejecutar la carga NoSQL

MongoDB debe estar disponible en una instancia local o remota. Con MongoDB local en el puerto predeterminado:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/populate_nosql.py --reset
```

Opciones principales:

```powershell
python scripts/populate_nosql.py `
  --mongo-uri "mongodb://localhost:27017/" `
  --database "SaberProDB" `
  --collection "Fact_Resultados" `
  --batch-size 10000 `
  --encoding auto `
  --reset
```

El parámetro `--encoding latin-1` puede utilizarse si la detección automática identifica caracteres incorrectamente. No use `--reset` si desea conservar los documentos existentes.

## Exportación filtrada (HU09)

La HU09 puede ejecutarse directamente con un script Python; no requiere que el backend web esté implementado.

Instale las dependencias del script:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r scripts/requirements.txt
```

Ejemplo CSV con filtros actuales:

```powershell
python scripts/export_data.py `
  --format csv `
  --year 2018 `
  --department BOGOTA `
  --institution UNIVERSIDAD `
  --reference-group ADMINISTRACION `
  --limit 10000 `
  --offset 0 `
  --output exports/saber-pro-2018-bogota.csv
```

Ejemplo JSON:

```powershell
python scripts/export_data.py --format json --year 2018 --limit 10000 --output exports/saber-pro-2018.json
```

Exportación por lotes:

```powershell
python scripts/export_data.py --format csv --limit 10000 --offset 0 --output exports/batch-1.csv
python scripts/export_data.py --format csv --limit 10000 --offset 10000 --output exports/batch-2.csv
python scripts/export_data.py --format csv --limit 10000 --offset 20000 --output exports/batch-3.csv
```

Las funciones reutilizables están en `scripts/export_data.py`:

- `build_filter()`: transforma filtros de dashboard a consulta MongoDB.
- `count_filtered_records()`: obtiene el total coincidente.
- `iter_filtered_records()`: genera registros por lotes.
- `export_filtered_data()`: crea CSV o JSON.

Parámetros de conexión opcionales mediante variables de entorno: `MONGO_URI`, `MONGO_DATABASE` y `MONGO_COLLECTION`. `--limit` está limitado a 100.000 registros por ejecución y `--batch-size` controla cuántos registros se procesan simultáneamente.

### 7.6.3 Dimensiones y Tabla de Hechos (Estructura en MongoDB)

Para el diseño de la base de datos NoSQL en MongoDB, se ha optado por un **Esquema de Estrella (Star Schema)**. Las 39 columnas de interés seleccionadas en la fase ETL han sido distribuidas lógicamente para optimizar las consultas del dashboard, separando los datos cuantitativos (hechos) de los datos descriptivos (dimensiones).

**1. Colección de Hechos: `Fact_Resultados`**
Contiene las métricas cuantitativas del desempeño y las llaves de referencia.
*   `_id`: ObjectId (Autogenerado por MongoDB).
*   `estu_consecutivo`: Texto (Identificador único del examinando).
*   `id_tiempo`: ObjectId (FK -> Dim_Tiempo).
*   `id_estudiante`: ObjectId (FK -> Dim_Estudiante).
*   `id_institucion`: ObjectId (FK -> Dim_Institucion).
*   `id_programa`: ObjectId (FK -> Dim_Programa).
*   `id_ubicacion_examen`: ObjectId (FK -> Dim_Ubicacion_Examen).
*   `mod_razona_cuantitat_punt`: Numérico.
*   `mod_comuni_escrita_punt`: Numérico.
*   `mod_lectura_critica_punt`: Numérico.
*   `mod_ingles_punt`: Numérico.
*   `mod_competen_ciudada_punt`: Numérico.
*   `mod_comuni_escrita_desem`: Texto (Nivel de desempeño).
*   `mod_ingles_desem`: Texto (Nivel de desempeño).

**2. Colección Dimensión: `Dim_Tiempo`**
*   `_id`: ObjectId.
*   `periodo`: Texto (Ej. "20225", "20212").

**3. Colección Dimensión: `Dim_Estudiante`**
Agrupa la información sociodemográfica y socioeconómica del examinado.
*   `_id`: ObjectId.
*   `estu_genero`: Texto.
*   `estu_fechanacimiento`: Fecha/Texto.
*   `estu_nacionalidad`: Texto.
*   `estu_pais_reside`: Texto.
*   `estu_depto_reside`: Texto.
*   `estu_mcpio_reside`: Texto.
*   `estu_privado_libertad`: Texto.
*   `estu_estudiante`: Texto.
*   `estu_horassemanatrabaja`: Texto.
*   `fami_educacionpadre`: Texto.
*   `fami_educacionmadre`: Texto.
*   `fami_estratovivienda`: Texto.
*   `fami_tienecomputador`: Texto.
*   `fami_tieneinternet`: Texto.
*   `estu_valormatriculauniversidad`: Texto.
*   `estu_pagomatriculabeca`: Texto.
*   `estu_pagomatriculacredito`: Texto.
*   `estu_pagomatriculapadres`: Texto.
*   `estu_pagomatriculapropio`: Texto.

**4. Colección Dimensión: `Dim_Institucion`**
*   `_id`: ObjectId.
*   `inst_nombre_institucion`: Texto.
*   `inst_caracter_academico`: Texto.
*   `inst_origen`: Texto.
*   `estu_cole_termino`: Texto.
*   `estu_inst_departamento`: Texto.
*   `estu_inst_municipio`: Texto.

**5. Colección Dimensión: `Dim_Programa`**
*   `_id`: ObjectId.
*   `estu_nucleo_pregrado`: Texto.
*   `estu_prgm_academico`: Texto.
*   `estu_metodo_prgm`: Texto.

**6. Colección Dimensión: `Dim_Ubicacion_Examen`**
*   `_id`: ObjectId.
*   `estu_depto_presentacion`: Texto.
*   `estu_mcpio_presentacion`: Texto.

### 7.6.4 Diagrama de la Base de Datos

A continuación, se presenta el diagrama del Esquema de Estrella implementado para la base de datos en MongoDB:

![Diagrama de la Base de Datos](docs/deepseek_mermaid_20261019_487784.png)

*Figura X. Diagrama del Esquema de Estrella para la base de datos SaberProDB en MongoDB.*

# Capítulo 7. Sistema Implementado

## 7.7 Proceso ETL (Extract, Transform, Load)

### 7.7.3 Carga de Datos a la Base de Datos NoSQL (Rutina Tentativa)

Para la carga inicial del dataset depurado (con un volumen superior a 1.000.000 de registros) hacia el motor NoSQL seleccionado (MongoDB), se ha diseñado una rutina en Python que garantiza la integridad de los datos y el rendimiento del sistema. Dado el alto volumen de información, no se realiza una inserción registro por registro (lo cual saturaría la memoria y el tiempo de ejecución), sino que se implementa una **estrategia de carga por lotes (Batching)**.

**Flujo lógico de la rutina:**
1. **Extracción:** El script lee el archivo CSV depurado y homologado (que contiene los datos unificados de los 5 años) utilizando la librería `pandas`.
2. **Conexión:** Se establece la conexión con la base de datos MongoDB mediante la librería `pymongo`, apuntando al clúster local o en la nube y a la base de datos `SaberProDB`.
3. **Transformación a Documentos (BSON):** Los datos tabulares se convierten en diccionarios de Python (que MongoDB almacena internamente como BSON). Siguiendo el Esquema de Estrella definido, los registros se preparan para poblar la colección de Hechos (`Fact_Resultados`) y las colecciones de Dimensiones (`Dim_Estudiante`, `Dim_Institucion`, `Dim_Tiempo`, etc.).
4. **Carga por Lotes:** Para evitar el desbordamiento de la memoria RAM, el script recorre el DataFrame en bloques (chunks) de 10.000 registros. Cada bloque se inserta en MongoDB utilizando el método `insert_many()`.
5. **Verificación:** Al finalizar el ciclo, el script realiza un conteo de los documentos en cada colección para confirmar que la carga se completó exitosamente y que el número de documentos coincide con las filas del CSV.

---

### Pseudocódigo de la Rutina de Carga

```text
INICIO
  // 1. Definir conexión
  cliente = Conectar_MongoDB("mongodb://localhost:27017/")
  db = cliente["SaberProDB"]
  
  // 2. Leer el dataset depurado (CSV)
  datos = Leer_CSV("dataset_saber_pro_5_anios.csv")
  
  // 3. Definir tamaño del lote
  TAMANO_LOTE = 10000
  total_registros = Contar_Filas(datos)
  
  // 4. Ciclo de carga por lotes
  PARA i = 0 HASTA total_registros PASO TAMANO_LOTE HACER:
      lote_actual = datos[i : i + TAMANO_LOTE]
      lista_documentos = Convertir_A_JSON(lote_actual)
      
      // Insertar en la colección de hechos
      db["Fact_Resultados"].insert_many(lista_documentos)
      
      Imprimir("Insertados registros del " + i + " al " + (i + TAMANO_LOTE))
  FIN PARA
  
  // 5. Verificar
  conteo_final = db["Fact_Resultados"].count_documents({})
  Imprimir("Carga finalizada. Total en BD: " + conteo_final)
FIN
```

```python 
import pandas as pd 
from pymongo import MongoClient 

# 1. Conexión a MongoDB 
cliente = MongoClient("mongodb://localhost:27017/") 
db = cliente["SaberProDB"] 
coleccion_hechos = db["Fact_Resultados"] 

# 2. Lectura del dataset depurado 
df = pd.read_csv("dataset_saber_pro_5_anios.csv") 

# 3. Carga por lotes (Batching) para optimizar memoria 
TAMANO_LOTE = 10000 
total_registros = len(df) 

print(f"Iniciando carga de {total_registros} registros...") 

for i in range(0, total_registros, TAMANO_LOTE): 
	# Extraer el lote actual 
	lote = df.iloc[i:i+TAMANO_LOTE] 
	
	# Convertir el lote a una lista de diccionarios (formato BSON/JSON) 
	documentos = lote.to_dict(orient="records") 
	
	# Inserción masiva en la colección 
	coleccion_hechos.insert_many(documentos) 
	print(f"Insertados {i + len(lote)} de {total_registros registros...") 
	
# 4. Verificación final 
conteo_final = coleccion_hechos.count_documents({}) 
print(f"¡Carga completada! Total de documentos en la BD: {conteo_final}") 
```
