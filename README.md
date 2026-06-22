<div align="center">

<img src="images/flux1.png" alt="FLUX Quant Logo" width="250" style="margin-bottom: 20px;"/>

# 📊 FLUX Quant

### Sistema Profesional de Análisis Técnico Cuantitativo Multi-Activo

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![yfinance](https://img.shields.io/badge/Data-Yahoo%20Finance-6001D2?style=for-the-badge&logo=yahoo&logoColor=white)](https://github.com/ranaroussi/yfinance)
[![Rich TUI](https://img.shields.io/badge/UI-Rich%20%2B%20Plotext%20TUI-E94F37?style=for-the-badge)](https://github.com/Textualize/rich)

<br/>

> **FLUX Quant** es un sistema de análisis técnico y cuantitativo de alto rendimiento construido íntegramente en Python. Combina 9 motores matemáticos —desde análisis clásico de Soportes/Resistencias hasta Machine Learning al vuelo con Random Forest y análisis espectral de Fourier— en una interfaz de terminal REPL interactiva y un Dashboard Web moderno impulsado por FastAPI.

<br/>

![Terminal Demo](https://img.shields.io/badge/Modo%20CLI%20--%20REPL%20Interactivo-blueviolet?style=flat-square)
![Web Dashboard](https://img.shields.io/badge/Modo%20WEB%20--%20Dashboard%20FastAPI-teal?style=flat-square)

</div>

---

## 📌 Tabla de Contenidos

1. [✨ Características Clave](#-características-clave)
2. [🏗️ Arquitectura del Sistema](#️-arquitectura-del-sistema)
3. [📁 Estructura del Proyecto](#-estructura-del-proyecto)
4. [⚙️ Instalación y Configuración](#️-instalación-y-configuración)
   - [Requisitos Previos](#requisitos-previos)
   - [🐧 Linux / macOS](#-linux--macos)
   - [🪟 Windows](#-windows)
   - [📦 Dependencias del Sistema](#-dependencias-del-sistema)
5. [🚀 Inicio Rápido](#-inicio-rápido)
   - [Modo Terminal (REPL)](#modo-terminal-repl)
   - [Modo Dashboard Web](#modo-dashboard-web)
6. [💻 Referencia de Comandos](#-referencia-de-comandos)
7. [⚙️ Configuración (config.toml)](#️-configuración-configtoml)
8. [🔬 Motores de Análisis](#-motores-de-análisis)
9. [🌐 API REST](#-api-rest)
10. [📊 Activos Soportados](#-activos-soportados)
11. [🛠️ Solución de Problemas](#️-solución-de-problemas)
12. [📄 Licencia](#-licencia)

---

## ✨ Características Clave

### 🧠 9 Motores de Análisis Integrados

| Motor | Descripción |
|---|---|
| **Soportes / Resistencias** | Pivotes Classic, Fibonacci, Camarilla, Woodie y DeMark · Fractales de Williams · Clustering cuantitativo de zonas |
| **Volume Profile (VPVR)** | POC (Point of Control) · VAH / VAL (Value Area) · VWAP acumulado con desviaciones estándar |
| **Fibonacci** | Retrocesos (0.236 – 0.786) · Extensiones (1.272 – 2.618) · Detección automática de swing y zonas de confluencia dorada |
| **Ángulos de Gann** | Abanico completo de 9 ángulos (82.5° – 7.5°) · Cuadrado de 9 · Ciclos temporales |
| **Imbalance / SMC** | Fair Value Gaps (FVG) alcistas y bajistas · Order Blocks institucionales · Liquidity Pools |
| **Volatilidad** | ATR dinámico · Bandas de Bollinger · Canal de Keltner · Percentiles históricos · Stops y TPs adaptativos |
| **Estructura de Mercado** | Detección automática de BOS (Break of Structure) y CHoCH (Change of Character) |
| **Indicadores Clásicos** | RSI · MACD · Oscilador Estocástico · ADX con filtros de fuerza de tendencia |
| **Motor Cuantitativo (Quant)** | Análisis de Ciclos FFT (Fourier) · Order Flow real cuando existe / VSA aproximado · Predicción ML con Random Forest en tiempo real |

### 🎯 Sistema de Señales y Gestión de Riesgo
- **Scoring Multi-confluencia**: Algoritmo propietario que pondera la señal de cada motor para generar una dirección (LONG / SHORT / NEUTRAL) con probabilidad de éxito estimada.
- **Gestión de Riesgo Dinámica**: Calcula automáticamente entrada, Stop-Loss y dos niveles de Take-Profit basados en ATR y capital configurado.
- **Position Sizing**: Cálculo del tamaño de posición óptimo según el porcentaje de riesgo por operación.

### 🖥️ Interfaces Duales

| Interfaz | Tecnología | Descripción |
|---|---|---|
| **Shell REPL Interactivo** | `prompt_toolkit` + `rich` + `plotext` | Autocompletado, historial de comandos, gráficos de velas en ASCII y dashboards multi-panel en la terminal |
| **Dashboard Web Profesional** | `FastAPI` + TradingView Lightweight Charts | Gráficos interactivos con indicadores superpuestos, niveles técnicos dibujados y panel de análisis en tiempo real |

### ⚡ Caché Inteligente Parquet
- Almacenamiento local de datos históricos en formato Parquet (columnar, comprimido).
- TTL configurable (por defecto 15 minutos) para reducir peticiones a Binance, MetaTrader 5 y Yahoo Finance.
- Invalidación automática al cambiar símbolo o timeframe.

---

## 🏗️ Arquitectura del Sistema

El sistema está diseñado con una arquitectura desacoplada y sin estado por activo, donde cada módulo puede operar de forma independiente:

```
┌─────────────────────────────────────────────────────────────┐
│                        USUARIO                              │
└────────────┬───────────────────────────┬────────────────────┘
             │ Terminal                  │ Navegador
             ▼                           ▼
    ┌─────────────────┐       ┌─────────────────────┐
    │  Shell REPL     │       │  Dashboard Web      │
    │ (prompt_toolkit)│       │  (FastAPI + HTML)   │
    └────────┬────────┘       └──────────┬──────────┘
             └──────────┬────────────────┘
                        ▼
             ┌─────────────────────┐
             │    DataProvider     │
             │  yfinance + Parquet │
             └──────────┬──────────┘
                        ▼
             ┌─────────────────────┐
             │  DataFrame OHLCV    │
             │     (pandas)        │
             └──────────┬──────────┘
                        ▼
        ┌───────────────────────────────┐
        │       Motores de Análisis     │
        │  S/R · Volume · Fibonacci     │
        │  Gann · Imbalance · Volatility│
        │  Structure · Indicators · ML  │
        └───────────────┬───────────────┘
                        ▼
             ┌─────────────────────┐
             │   Report Engine     │
             │  + Scoring Signal   │
             └──────────┬──────────┘
                        ▼
           ┌────────────────────────┐
           │      Capa de Salida    │
           │  Tablas Rich / Charts  │
           │  JSON API / TradingView│
           └────────────────────────┘
```

---

## 📁 Estructura del Proyecto

```
FLUX_Quant/
│
├── 📄 main.py                    # Punto de entrada · verifica deps · despacha CLI o Web
├── 📄 config.toml                # Configuración global parametrizable
├── 📄 requirements.txt           # Dependencias del sistema
├── 📄 setup_env.sh               # Script de instalación automática (Linux / macOS)
├── 📄 setup_env.bat              # Script de instalación automática (Windows)
├── 📄 activate_env.sh            # Atajo para activar el entorno virtual
├── 📄 .gitignore                 # Exclusiones de Git
├── 📄 LICENSE                    # Licencia MIT
│
├── 📂 core/                      # Núcleo del sistema
│   ├── config.py                 # Cargador de config.toml en caliente
│   ├── data_provider.py          # Descargador con caché Parquet + yfinance
│   ├── binance_provider.py       # Proveedor de datos Binance (order flow real)
│   └── session.py                # Estado de la sesión activa
│
├── 📂 analysis/                  # Motores de análisis matemático y cuantitativo
│   ├── support_resistance.py     # Pivotes clásicos, fractales, clustering
│   ├── volume_analysis.py        # Volume Profile (VPVR), VWAP, OBV
│   ├── fibonacci.py              # Retrocesos, extensiones y confluencias
│   ├── gann.py                   # Abanico de Gann y Cuadrado de 9
│   ├── imbalance.py              # Fair Value Gaps (FVG) y Order Blocks
│   ├── volatility.py             # ATR, Bollinger, Keltner, stops dinámicos
│   ├── indicators.py             # RSI, MACD, Estocástico, ADX
│   ├── market_structure.py       # Detector de BOS y CHoCH
│   ├── quant.py                  # FFT + Order Flow CVD/VSA + ML Random Forest
│   └── report_engine.py          # Consolidador de resultados + scoring final
│
├── 📂 ui/                        # Interfaz gráfica de terminal (TUI)
│   ├── shell.py                  # Shell REPL interactivo con prompt_toolkit
│   ├── charts.py                 # Graficador de velas japonesas con plotext
│   ├── tables.py                 # Constructor de tablas estructuradas con rich
│   ├── dashboard.py              # Layout multi-panel
│   ├── colors.py                 # Paleta de colores ANSI y estilos rich
│   └── formatters.py             # Formateadores numéricos de alta precisión
│
├── 📂 web/                       # API REST y Dashboard Web
│   ├── api.py                    # Endpoints FastAPI: /api/ohlcv, /api/indicators, /api/analysis
│   └── static/                   # Frontend estático servido por FastAPI
│       ├── index.html            # Dashboard web principal
│       ├── dashboard.js          # Lógica (TradingView Lightweight Charts)
│       └── styles.css            # Estilos del dashboard
│
├── 📂 utils/                     # Utilidades transversales
│   ├── validators.py             # Validación de entradas del usuario
│   └── logger.py                 # Sistema de logging a archivo
│
├── 📂 data/raw/                  # (Auto-creado) Datos descargados sin procesar
├── 📂 .cache/                    # (Auto-creado) Caché Parquet de series históricas
├── 📂 logs/                      # (Auto-creado) Archivos de log del sistema
└── 📂 exports/                   # (Auto-creado) CSVs exportados por el usuario
```

---

## ⚙️ Instalación y Configuración

### Requisitos Previos

| Requisito | Versión Mínima | Cómo verificar |
|---|---|---|
| **Python** | 3.10 | `python --version` |
| **pip** | 23+ | `pip --version` |
| **Git** | cualquiera | `git --version` |
| **Conexión a Internet** | — | Para descargar datos de Binance/Yahoo Finance |

> ⚠️ El sistema fue desarrollado y probado en Python **3.10, 3.11 y 3.12**. No se garantiza compatibilidad con Python 3.9 o inferior.

---

### Instalación Automática Universal (Recomendada)

Hemos unificado la instalación para Windows, Linux y macOS en un solo comando:

```bash
# 1. Clonar el repositorio
git clone https://github.com/QuantLlama/FLUX_Quant.git
cd FLUX_Quant

# 2. Ejecutar el instalador universal
python install.py
```

El instalador detectará tu sistema operativo automáticamente y realizará:
- ✅ Verificación de Python 3.10+
- ✅ Creación del entorno virtual `.venv` (con fallback inteligente en Linux si hay problemas de permisos en discos externos)
- ✅ Actualización de `pip`
- ✅ Instalación de todas las dependencias de `requirements.txt`
- ✅ Creación de directorios de trabajo (`.cache/`, `logs/`, `exports/`, `data/raw/`)

### Lanzamiento Rápido 🚀

¡Ya no necesitas activar el entorno virtual manualmente! Puedes usar nuestros atajos globales multiplataforma:

**En Linux / macOS:**
```bash
./flux
```

**En Windows:**
```cmd
flux
```
Esto activará el entorno en segundo plano y lanzará el asistente interactivo de trading al instante.

---

### Instalación Manual (Avanzada)

Si prefieres configurar todo por tu cuenta o integrarlo en tus propios scripts:

#### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p .cache logs exports data/raw
```

#### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
New-Item -ItemType Directory -Force -Path .cache, logs, exports, "data\raw"
```

#### Activar el Entorno en Sesiones Futuras (Instalación Manual)

**Linux / macOS:**
```bash
source .venv/bin/activate
```

**Windows:**
```cmd
.venv\Scripts\activate.bat
```
:: CMD
.venv\Scripts\activate.bat

:: PowerShell
.venv\Scripts\Activate.ps1
```

---

### 📦 Dependencias del Sistema

| Librería | Versión Mín. | Propósito |
|---|---|---|
| `yfinance` | ≥ 0.2.38 | Fallback de datos históricos OHLCV |
| `MetaTrader5` | ≥ 5.0.45 | Datos MT5 opcionales para forex, futuros, commodities, CFDs y acciones |
| `pandas` | ≥ 2.0.0 | Manipulación de series temporales y DataFrames |
| `numpy` | ≥ 1.26.0 | Cálculos vectorizados y FFT |
| `rich` | ≥ 13.7.0 | Tablas, colores y layout de la TUI |
| `prompt_toolkit` | ≥ 3.0.43 | Shell REPL con autocompletado e historial |
| `plotext` | ≥ 5.2.8 | Gráficos de velas y líneas en la terminal |
| `toml` | ≥ 0.10.2 | Lectura del archivo `config.toml` |
| `pydantic` | ≥ 2.0.0 | Validación de datos para la API REST |
| `joblib` | ≥ 1.3.0 | Paralelización y serialización |
| `pyarrow` | ≥ 15.0.0 | Motor Parquet para la caché de datos |
| `colorama` | ≥ 0.4.6 | Compatibilidad de colores ANSI en Windows |
| `scipy` | ≥ 1.12.0 | Cálculos estadísticos y de señales |
| `requests` | ≥ 2.31.0 | Peticiones HTTP |
| `fastapi` | ≥ 0.100.0 | Framework API REST para el Dashboard Web |
| `uvicorn` | ≥ 0.23.0 | Servidor ASGI para FastAPI |

> 💡 **Opcional:** `scikit-learn` activa el motor de **Predicción ML con Random Forest**.
> ```bash
> pip install scikit-learn
> ```

---

## 🚀 Inicio Rápido

### Modo Terminal (REPL)

```bash
# Activar el entorno (si no está activo)
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate.bat     # Windows

# Iniciar el shell interactivo
./flux
```

Verás el prompt del sistema:

```
╔══════════════════════════════════════════════╗
║    📊 Sistema de Análisis Financiero v2.0    ║
╚══════════════════════════════════════════════╝

FLUXQuant@BTC-USD:1d >
```

**Sesión de ejemplo básica:**

```
FLUXQuant@BTC-USD:1d  > set symbol AAPL
FLUXQuant@AAPL:1d     > set timeframe 4h
FLUXQuant@AAPL:4h     > chart candles
FLUXQuant@AAPL:4h     > analyze quant
FLUXQuant@AAPL:4h     > dashboard
FLUXQuant@AAPL:4h     > report
```

---

### Modo Dashboard Web

```bash
source .venv/bin/activate
./flux web
```

Servidor FastAPI en `http://localhost:8555`

El Dashboard incluye:
- 📈 Gráfico de velas interactivo (TradingView Lightweight Charts)
- 🔵 EMAs (9, 21, 50, 200) superpuestas
- 📊 Bandas de Bollinger y VWAP
- 📐 Niveles de Soporte/Resistencia
- 🌀 Retrocesos de Fibonacci
- 📉 Fair Value Gaps (FVG) coloreados
- 🎯 Panel de señal con dirección, score y setup de riesgo

**Documentación interactiva de la API:**
```
http://localhost:8555/docs    # Swagger UI
http://localhost:8555/redoc   # ReDoc
```

---

## 💻 Referencia de Comandos

### ⚙️ Configuración de Sesión

| Comando | Descripción | Ejemplo |
|---|---|---|
| `set symbol <TICKER>` | Cambia el activo y descarga datos | `set symbol ETH-USD` |
| `set timeframe <TF>` | Cambia el timeframe | `set timeframe 4h` |
| `set period <PER>` | Cambia el rango histórico | `set period 6mo` |
| `fetch` | Fuerza recarga desde Binance/MT5 con fallback a Yahoo Finance (ignora caché) | `fetch` |
| `test connections` | Verifica conexiones Binance y MetaTrader 5 | `test connections` |

**Timeframes:** `1m` `2m` `5m` `15m` `30m` `60m` `90m` `1h` `4h` `1d` `5d` `1wk` `1mo` `3mo`

**Períodos:** `1d` `5d` `1mo` `3mo` `6mo` `1y` `2y` `5y` `10y` `ytd` `max`

---

### 🔬 Análisis

| Comando | Motor Activado | Descripción |
|---|---|---|
| `analyze sr` | Soportes / Resistencias | Pivotes, fractales y zonas clusterizadas |
| `analyze volume` | Volume Profile | POC, VAH, VAL, VWAP y absorción |
| `analyze fib` | Fibonacci | Retrocesos, extensiones y confluencias |
| `analyze gann` | Ángulos de Gann | Abanico completo y Cuadrado de 9 |
| `analyze imbalance` | Imbalance / SMC | Fair Value Gaps y Order Blocks |
| `analyze volatility` | Volatilidad | ATR, Bollinger, Keltner, stops/TPs |
| `analyze structure` | Estructura de Mercado | BOS y CHoCH |
| `analyze quant` | Motor Cuantitativo | FFT + Order Flow CVD/VSA + ML Random Forest |
| `indicator rsi` | RSI | Índice de Fuerza Relativa (14p) |
| `indicator macd` | MACD | MACD (12/26/9) con histograma |
| `indicator stoch` | Estocástico | %K y %D |
| `indicator adx` | ADX | Fuerza de tendencia direccional |
| `indicator all` | Todos | Calcula todos los indicadores |
| `analyze all` | **Todos los motores** | Reporte completo con 9 motores + scoring |

---

### 📊 Visualización

| Comando | Descripción |
|---|---|
| `chart candles` | Layout dual: velas japonesas + volumen + EMAs (9/21/50) |
| `chart rsi` | RSI(14) con zonas de sobrecompra/sobreventa |
| `chart macd` | MACD + señal + histograma |
| `dashboard` | Dashboard multi-panel en pantalla completa |
| `report` | Informe técnico completo con tablas enriquecidas |

---

### 📋 Watchlist y Comparación

| Comando | Descripción | Ejemplo |
|---|---|---|
| `watchlist add <TICKER>` | Agrega a la watchlist | `watchlist add SOL-USD` |
| `watchlist defaults` | Carga la watchlist multi-mercado por defecto | `watchlist defaults` |
| `watchlist remove <TICKER>` | Elimina de la watchlist | `watchlist remove SOL-USD` |
| `watchlist show` | Muestra la watchlist | `watchlist show` |
| `watchlist scan` | Escanea rendimiento/volatilidad de la watchlist | `watchlist scan` |
| `compare <T1> <T2> ...` | Compara múltiples activos | `compare BTC-USD ETH-USD GC=F` |

---

### 🗂️ Gestión

| Comando | Descripción |
|---|---|
| `config show` | Muestra los parámetros de `config.toml` |
| `cache clear` | Limpia la caché Parquet local |
| `export csv` | Exporta datos del activo actual a `/exports/` |
| `help` | Lista completa de comandos |
| `exit` / `quit` | Cierra el shell |

---

## ⚙️ Configuración (config.toml)

Todos los parámetros del sistema son configurables sin modificar el código fuente:

```toml
[general]
default_symbol    = "BTC-USD"   # Activo por defecto al iniciar
default_timeframe = "1d"        # Timeframe por defecto
default_period    = "1y"        # Rango histórico por defecto
theme             = "dark"      # "dark" | "light"

[data]
cache_enabled     = true        # Activar/desactivar la caché Parquet
cache_ttl_minutes = 15          # Tiempo de vida de la caché (minutos)

[mt5]
terminal_path = ""              # Opcional; vacío usa detección de MetaTrader 5
max_bars = 5000

[mt5.symbol_aliases]            # Ajustar según nombres del broker
"NQ=F" = ["NAS100", "US100", "USTEC", "NQ"]
"GC=F" = ["XAUUSD", "GOLD", "GC"]

[watchlist]
default_symbols = ["BTC-USD", "ETH-USD", "EURUSD=X", "NQ=F", "ES=F", "GC=F", "CL=F", ...]

[fibonacci]
levels     = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
extensions = [1.272, 1.618, 2.0, 2.618]

[gann]
angles = [82.5, 75.0, 63.75, 45.0, 26.25, 15.0, 7.5]

[volatility]
atr_period          = 14
atr_sl_multiplier   = 2.0   # Multiplicador ATR para Stop-Loss
atr_tp_multiplier_1 = 3.0   # Multiplicador ATR para TP1
atr_tp_multiplier_2 = 5.0   # Multiplicador ATR para TP2

[indicators]
rsi_period  = 14
macd_fast   = 12
macd_slow   = 26
macd_signal = 9
ema_periods = [9, 21, 50, 200]

[risk]
default_capital      = 10000.0  # Capital base para cálculo de posición
default_risk_percent = 1.0      # % de capital en riesgo por operación
default_rr_ratio     = 2.0      # Ratio Riesgo/Recompensa mínimo

[screener]
crypto_symbols    = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", ...]
forex_symbols     = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", ...]
commodity_symbols = ["GC=F", "SI=F", "CL=F", ...]
indices_symbols   = ["^GSPC", "^NDX", "^DJI", ...]
```

---

## 🔬 Motores de Análisis

### 🤖 Motor Cuantitativo (Quant) — `analysis/quant.py`

El motor más avanzado del sistema combina tres enfoques con ponderación adaptativa:

#### 1. Análisis de Ciclos con FFT (Fourier Transform) — Peso: 25%

- Aplica la **Transformada de Fourier Rápida (FFT)** sobre los precios detrended.
- Identifica los **3 ciclos dominantes** de la serie temporal.
- Determina la **fase actual**: *Expansión (Alcista)* o *Contracción (Bajista)*.

#### 2. Order Flow / VSA — Peso: 35%

- En crypto usa volumen taker real de Binance cuando está disponible.
- Si crypto cae a Yahoo Finance, no inventa buy/sell volume sintético.

- **Con datos Binance:** usa Taker Buy/Sell Volume para calcular el **CVD real**.
- **Con MT5/Yahoo no-crypto:** aplica **VSA (Volume Spread Analysis)** calculando la presión compradora/vendedora a partir del cuerpo normalizado de la vela `(Close - Open) / (High - Low)`.
- Detecta **divergencias precio/CVD** para identificar absorciones e impulsos institucionales.

| Estado | Condición |
|---|---|
| Divergencia Bajista (Absorción) | Precio ↑ pero CVD ↓ |
| Divergencia Alcista (Acumulación) | Precio ↓ pero CVD ↑ |
| Agresión de Compra Confirmada | Precio ↑ y CVD ↑ |
| Agresión de Venta Confirmada | Precio ↓ y CVD ↓ |

#### 3. Predicción ML — Random Forest al Vuelo — Peso: 40%

- Entrena un **Random Forest Classifier** en tiempo de ejecución con el histórico completo del activo.
- **Features:** Retornos, Volatilidad relativa, Distancia a SMA(20), RSI(14).
- **Target:** ¿El precio cierra por encima en las próximas 3 velas?
- Escala la probabilidad a un score de **-1.0 (venta fuerte)** a **+1.0 (compra fuerte)**.
- Requiere `scikit-learn`. Si no está instalado, el sistema funciona sin esta componente.

#### Score Final Ensamble

```
Score_Final = (Score_Fourier × 0.25) + (Score_OrderFlow × 0.35) + (Score_ML × 0.40)
```

| Score Final | Señal |
|---|---|
| `> +0.30` | **COMPRA (LONG)** |
| `< -0.30` | **VENTA (SHORT)** |
| `Entre -0.30 y +0.30` | **NEUTRAL** |

---

## 🌐 API REST

**Base URL:** `http://localhost:8555`

### Endpoints

#### `GET /api/ohlcv/{symbol}`
Retorna velas OHLCV en formato TradingView Lightweight Charts.

```
GET /api/ohlcv/AAPL?timeframe=1d&period=1y
```

**Respuesta:**
```json
{
  "symbol": "AAPL",
  "timeframe": "1d",
  "candles": [
    { "time": 1704067200, "open": 185.0, "high": 188.5, "low": 183.2, "close": 187.1, "volume": 55000000 }
  ]
}
```

---

#### `GET /api/indicators/{symbol}`
Retorna series temporales de indicadores técnicos para superponer en el gráfico.

```
GET /api/indicators/BTC-USD?timeframe=1d&period=1y
```

Incluye: `emas` (9, 21, 50, 200), `bollinger` (upper, middle, lower), `rsi`, `macd` (macd, signal, histogram), `vwap`.

---

#### `GET /api/analysis/{symbol}`
Ejecuta **todos los motores** y retorna el reporte completo con señal de trading.

```
GET /api/analysis/ETH-USD?timeframe=4h&period=6mo&capital=50000&risk=1.5
```

**Respuesta (resumen):**
```json
{
  "symbol": "ETH-USD",
  "price": 3450.20,
  "direction": "COMPRA (LONG)",
  "score_buy": 72.5,
  "setup": {
    "entry": 3450.20,
    "stop_loss": 3380.15,
    "take_profit_1": 3590.50,
    "take_profit_2": 3730.80
  },
  "market_structure": { "trend": "bullish" },
  "volatility": { "atr": 85.30, "regime": "Normal" },
  "sr_levels": [...],
  "fib_levels": [...],
  "fvgs": [...],
  "indicators": { "rsi": 58.4, "macd": 12.3, "adx": 28.7 },
  "quant": { "direction": "COMPRA (LONG)", "fourier": {...}, "order_flow": {...}, "ml_data": {...} }
}
```

---

#### `GET /api/watchlist/scan`
Escanea múltiples activos y retorna un resumen comparativo.

```
GET /api/watchlist/scan?symbols=BTC-USD,ETH-USD,SOL-USD,GC=F&timeframe=1d
```

---

## 📊 Activos Soportados

El sistema soporta cualquier ticker válido en Yahoo Finance:

| Categoría | Ejemplos de Tickers |
|---|---|
| **Criptomonedas** | `BTC-USD` `ETH-USD` `SOL-USD` `BNB-USD` `XRP-USD` `AVAX-USD` |
| **Acciones USA** | `AAPL` `MSFT` `TSLA` `NVDA` `AMZN` `GOOGL` `META` |
| **Forex** | `EURUSD=X` `GBPUSD=X` `USDJPY=X` `AUDUSD=X` |
| **Materias Primas** | `GC=F` (Oro) `SI=F` (Plata) `CL=F` (Petróleo) `NG=F` (Gas Natural) |
| **Índices** | `^GSPC` (S&P500) `^NDX` (Nasdaq100) `^DJI` (Dow Jones) `^DAX` |
| **Futuros** | `ES=F` `NQ=F` `YM=F` `RTY=F` |

---

## 🛠️ Solución de Problemas

### ❌ Faltan dependencias críticas

```
❌ ERROR: Faltan dependencias críticas de Python:
   • yfinance
   • rich
```

**Solución:** Activa el entorno virtual antes de ejecutar:
```bash
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate.bat     # Windows
pip install -r requirements.txt
```

---

### ❌ Error al crear el entorno virtual en disco externo

En discos externos (NTFS, exFAT) montados en Linux, `venv` puede fallar al crear symlinks. El script `setup_env.sh` detecta esto automáticamente y crea el venv en `~/.venv_flux_quant`. Usa `source activate_env.sh` para activarlo.

---

### ⚠️ Motor ML no disponible

```
ML | No disponible / Datos Insuficientes
```

**Solución 1:** Instala `scikit-learn`:
```bash
pip install scikit-learn
```
**Solución 2:** Usa un período histórico más largo (mínimo 100 velas):
```
set period 1y
```

---

### ⚠️ Sin datos para el símbolo

Verifica que el ticker sea válido en [Yahoo Finance](https://finance.yahoo.com/):
- **Forex:** llevan sufijo `=X` → `EURUSD=X`
- **Futuros:** llevan sufijo `=F` → `GC=F`
- **Criptos:** llevan `-USD` → `BTC-USD`

---

## 📄 Licencia

Este proyecto está distribuido bajo la **Licencia MIT**. Consulta el archivo [LICENSE](LICENSE) para el texto completo.

---

<div align="center">

**Construido con ❤️ por [QuantLlama](https://github.com/QuantLlama)**

*"El mercado no miente. El análisis sí puede."*

[![GitHub](https://img.shields.io/badge/GitHub-QuantLlama-181717?style=for-the-badge&logo=github)](https://github.com/QuantLlama)

</div>
