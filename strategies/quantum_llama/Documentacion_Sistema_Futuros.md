# Documentación del Algoritmo Quantum Llama

El sistema **Quantum Llama** es un modelo híbrido cuantitativo y de Deep Learning optimizado para la predicción de precios y retornos en mercados de futuros, acciones y criptomonedas. Combina modelos estadísticos tradicionales, machine learning y redes neuronales recurrentes en un flujo secuencial de alta eficiencia.

## 1. Arquitectura y Componentes del Sistema

El flujo de ejecución del algoritmo está dividido en cuatro fases principales para maximizar la robustez del modelo frente a la volatilidad del mercado:

### A. Preprocesamiento e Ingeniería de Características (Features)
* **Indicadores Técnicos**: Generación automática de métricas de momento, tendencia y volatilidad (RSI, ADX, ATR, bandas de Bollinger, flujos de volumen).
* **Transformada de Fourier**: Descomposición espectral de la serie de precios para filtrar el ruido y extraer los ciclos estacionales predominantes en diferentes frecuencias.
* **Autoencoder Neuronal**: Red neuronal densa que proyecta el set de indicadores de alta dimensionalidad a un espacio latente optimizado (representación comprimida de baja dimensionalidad) eliminando la colinealidad.

### B. Modelado Estadístico y Probabilístico
* **ARIMA (Filtro Lineal)**: Modelo clásico autoregresivo que captura las relaciones lineales a corto plazo de la serie temporal del precio.
* **Regresión por Procesos Gaussianos (GPR)**: Modelo no paramétrico bayesiano que predice la tendencia del precio de cierre y proporciona un intervalo de incertidumbre probabilística (desviación estándar $\sigma$) del pronóstico.
* **Random Forest Feature Importance**: Evaluación de la importancia relativa de cada variable para descartar features irrelevantes y mitigar el sobreajuste.

### C. Red Neuronal Recurrente (LSTM Supervisada)
* **Entrenamiento con LSTM**: Red neuronal recurrente (Long Short-Term Memory) de múltiples capas diseñada específicamente para aprender secuencias históricas y dependencias de largo plazo.
* **Optimización y Regularización**: Uso de clip de gradiente para prevenir gradientes explosivos, scheduler de tasa de aprendizaje ReduceLROnPlateau y Early Stopping basado en el set de validación.

### D. Backtesting y Simulación Real
* **Evaluación Fuera de Muestra (Out-of-Sample)**: Verificación del rendimiento y métricas del modelo utilizando estrictamente el último 20% de los datos históricos que el modelo jamás vio durante el entrenamiento.
* **Simulador de Capital**: Simulación realista de trading con spreads, comisiones y reinversión para medir el retorno total, tasa de acierto (Win Rate) y la precisión direccional.

## 2. Parámetros del Modelo

El modelo se configura mediante los siguientes hiperparámetros ajustables desde el panel de control interactivo de FLUX:
* **seq_length**: Cantidad de velas históricas que observa el LSTM para realizar la predicción de la siguiente vela.
* **epochs**: Iteraciones máximas de entrenamiento (controladas por el callback de Early Stopping para evitar overfitting).
* **hidden_dim**: Cantidad de neuronas ocultas en las capas recurrentes LSTM del generador.
* **num_layers**: Profundidad (número de capas apiladas) de la red LSTM.

## 3. Interpretación del Dashboard

El dashboard dinámico muestra métricas clave de validación:
* **Direccional Accuracy**: Porcentaje de veces que el modelo acertó la dirección del movimiento (al alza o a la baja). Un valor superior al 52% suele ser altamente rentable en trading sistemático.
* **RMSE**: Error cuadrático medio de los retornos logarítmicos. Menores valores indican predicciones más precisas.
* **Total Return %**: Rendimiento acumulado de la estrategia simulada sobre el capital inicial de prueba.
