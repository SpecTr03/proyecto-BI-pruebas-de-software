# proyecto-BI-pruebas-de-software
Proyecto final de pruebas de software que tiene como objetivo crear un proceso ETL para posteriormente presentar los resultados en un dashboard, facilitando la toma de decisiones.

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
