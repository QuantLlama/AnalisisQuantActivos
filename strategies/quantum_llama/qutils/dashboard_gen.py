import os
import base64
from datetime import datetime

class DashboardGenerator:
    def __init__(self, output_dir='outputs'):
        self.output_dir = output_dir
        self.plots_dir = os.path.join(output_dir, 'plots')
        self.html_path = os.path.join(output_dir, 'dashboard.html')
        
    def _encode_image(self, image_path):
        """Encodes an image to base64 for embedding in HTML."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            return None

    def generate_dashboard(self, ticker, metrics, backtest_metrics, signals_df, history=None, asset_type="Futures", timeframe="1h"):
        """Generates the HTML dashboard."""
        
        # Construct filename prefix
        safe_ticker = ticker.replace("=", "").replace("-", "")
        prefix = f"{safe_ticker}_{timeframe}"
        
        # Encode FLUX Logo
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'web', 'static', 'fluxF1.png')
        img_logo = self._encode_image(logo_path)
        
        # Encode images with prefix
        img_correlation = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_correlation_matrix.png'))
        img_dashboard = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_technical_dashboard.png'))
        img_arima = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_arima_forecast.png'))
        img_gpr = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_gaussian_process.png'))
        img_sentiment = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_sentiment_analysis.png'))
        img_features = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_feature_importance.png'))
        img_fourier = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_fourier_analysis.png'))
        
        # Evolution images
        img_epoch_1 = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_prediction_epoch_1.png'))
        img_epoch_50 = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_prediction_epoch_50.png'))
        img_epoch_200 = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_prediction_epoch_200.png'))
        img_final = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_prediction_final.png'))
        
        # Additional Training Metrics
        img_losses = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_training_losses.png'))
        img_features_overview = self._encode_image(os.path.join(self.plots_dir, f'{prefix}_features_overview.png'))
        
        # Interpret Metrics
        rmse_color = "green" if metrics['RMSE'] < 0.001 else "orange" # Adjusted for Log Returns
        acc_color = "green" if metrics['Accuracy'] > 0.55 else "orange" if metrics['Accuracy'] > 0.50 else "red"
        
        advice = "El modelo muestra un rendimiento sólido."
        if metrics['Accuracy'] < 0.50:
            advice = "El modelo no está aprendiendo (Accuracy < 50%). Se recomienda revisar los datos o hiperparámetros."
        elif metrics['Accuracy'] < 0.55:
            advice = "El modelo es aceptable pero podría mejorar. Intenta ajustar el Learning Rate o añadir más indicadores."
            
        # Generate Signals Table HTML
        signals_html = ""
        # Show last 10 signals
        last_signals = signals_df.tail(10)
        
        # Get the very last signal for the Strategy Panel
        latest_signal = last_signals.iloc[-1]
        current_price = latest_signal['Price']
        signal_type = latest_signal['Signal']
        
        # Calculate Volatility (Standard Deviation of last 20 periods)
        volatility = signals_df['Price'].tail(20).std()
        
        # Dynamic TP/SL Logic (Simple ATR-like approach)
        # For Futures Scalping: SL = 1.5 * Volatility, TP = 2.5 * Volatility
        sl_points = volatility * 1.5
        tp_points = volatility * 2.5
        
        if signal_type == "BUY":
            rec_sl = current_price - sl_points
            rec_tp = current_price + tp_points
            action_color = "var(--success-color)"
            action_icon = "🚀"
        elif signal_type == "SELL":
            rec_sl = current_price + sl_points
            rec_tp = current_price - tp_points
            action_color = "var(--danger-color)"
            action_icon = "🔻"
        else:
            rec_sl = 0
            rec_tp = 0
            action_color = "var(--warning-color)"
            action_icon = "⏸️"

        # Strategy Panel HTML
        strategy_html = f"""
        <div class="card" style="border: 2px solid {action_color}; background: linear-gradient(180deg, rgba(30,30,36,1) 0%, rgba(10,10,15,1) 100%);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <div>
                    <h3 style="margin: 0; color: {action_color}; font-size: 1.5rem;">{action_icon} SEÑAL ACTUAL: {signal_type}</h3>
                    <p style="margin: 5px 0 0; color: #888; font-size: 0.9rem;">Estilo Sugerido: <strong style="color: #fff;">Scalping / Intraday</strong></p>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 2rem; font-weight: bold; color: #fff;">{current_price:.2f}</div>
                    <div style="font-size: 0.8rem; color: #666;">Precio Actual</div>
                </div>
            </div>
            
            <div class="grid-3" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; text-align: center;">
                <div style="background: rgba(239, 68, 68, 0.1); padding: 10px; border-radius: 8px; border: 1px solid rgba(239, 68, 68, 0.3);">
                    <div style="color: #ef4444; font-size: 0.8rem; font-weight: bold;">STOP LOSS (Sugerido)</div>
                    <div style="font-size: 1.2rem; color: #fff; margin-top: 5px;">{rec_sl:.2f}</div>
                    <div style="font-size: 0.7rem; color: #aaa;">-{sl_points:.2f} pts</div>
                </div>
                
                <div style="background: rgba(251, 191, 36, 0.1); padding: 10px; border-radius: 8px; border: 1px solid rgba(251, 191, 36, 0.3);">
                    <div style="color: #fbbf24; font-size: 0.8rem; font-weight: bold;">RIESGO / BENEFICIO</div>
                    <div style="font-size: 1.2rem; color: #fff; margin-top: 5px;">1 : {(tp_points/sl_points if sl_points > 0 else 0):.1f}</div>
                    <div style="font-size: 0.7rem; color: #aaa;">Ratio</div>
                </div>
                
                <div style="background: rgba(16, 185, 129, 0.1); padding: 10px; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3);">
                    <div style="color: #34d399; font-size: 0.8rem; font-weight: bold;">TAKE PROFIT (Sugerido)</div>
                    <div style="font-size: 1.2rem; color: #fff; margin-top: 5px;">{rec_tp:.2f}</div>
                    <div style="font-size: 0.7rem; color: #aaa;">+{tp_points:.2f} pts</div>
                </div>
            </div>
            
            <div style="margin-top: 15px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 6px; font-size: 0.85rem; color: #ccc;">
                <strong>ℹ️ Nota Operativa:</strong> Estos niveles son dinámicos y se basan en la volatilidad actual ({volatility:.2f} pts). Ajuste según su gestión de riesgo personal.
            </div>
        </div>
        """

        for _, row in last_signals.iterrows():
            signal_class = "badge-buy" if row['Signal'] == "BUY" else "badge-sell" if row['Signal'] == "SELL" else "badge-hold"
            signals_html += f"""
            <tr>
                <td>{row['Date'].strftime('%Y-%m-%d')}</td>
                <td>{row['Price']:.2f}</td>
                <td>{row['Prediction']:.2f}</td>
                <td><span class="badge {signal_class}">{row['Signal']}</span></td>
                <td>{row['Position']}</td>
            </tr>
            """
            
        # Comparative Analysis HTML
        comparative_html = ""
        if history:
            import pandas as pd
            hist_df = pd.DataFrame(history)
            if not hist_df.empty and 'asset_type' in hist_df.columns:
                # Group by Asset Type and calculate mean Win Rate and Return
                perf_by_type = hist_df.groupby('asset_type')[['win_rate', 'total_return']].mean().reset_index()
                
                # Find best asset class
                best_asset = perf_by_type.loc[perf_by_type['total_return'].idxmax()]
                
                comparative_html = f"""
                <div class="card" style="margin-top: 20px; border: 1px solid var(--accent-color);">
                    <h3 style="font-size: 1.1rem;">🏆 Análisis Comparativo Multi-Activo</h3>
                    <p style="font-size: 0.9rem;">Basado en tu historial de entrenamiento, aquí es donde tu IA brilla más:</p>
                    <div class="metrics-grid" style="margin-bottom: 15px;">
                        <div class="card" style="background: #2a2a2a; padding: 15px;">
                            <div class="metric-label" style="font-size: 0.75em;">Mejor Clase de Activo</div>
                            <div class="metric-value" style="color: var(--accent-color); font-size: 1.5em;">{best_asset['asset_type']}</div>
                            <small style="font-size: 0.8em;">Retorno Promedio: {best_asset['total_return']:.2f}%</small>
                        </div>
                    </div>
                    
                    <h4 style="font-size: 1rem;">Rendimiento Promedio por Tipo</h4>
                    <table style="width: 60%; font-size: 0.85rem;">
                        <thead>
                            <tr>
                                <th>Tipo de Activo</th>
                                <th>Win Rate Promedio</th>
                                <th>Retorno Promedio</th>
                                <th>Último Entrenamiento</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                for _, row in perf_by_type.iterrows():
                    # Find the latest date for this asset type
                    latest_date = hist_df[hist_df['asset_type'] == row['asset_type']]['date'].max()
                    
                    comparative_html += f"""
                    <tr>
                        <td>{row['asset_type']}</td>
                        <td>{row['win_rate']:.2f}%</td>
                        <td>{row['total_return']:.2f}%</td>
                        <td>{latest_date}</td>
                    </tr>
                    """
                
                comparative_html += """
                        </tbody>
                    </table>
                </div>
                """

        # Read Documentation Content
        doc_content = ""
        try:
            doc_path = os.path.abspath("Documentacion_Sistema_Futuros.md")
            if not os.path.exists(doc_path):
                # Try one level up (if run from strategies/quantum_llama/qutils)
                doc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Documentacion_Sistema_Futuros.md")
            if not os.path.exists(doc_path):
                # Try in the same folder as this file
                doc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Documentacion_Sistema_Futuros.md")
                
            if os.path.exists(doc_path):
                with open(doc_path, "r", encoding="utf-8") as f:
                    doc_lines = f.readlines()
                    
                # Improved Markdown to HTML parser
                html_doc = ""
                import re
                
                def slugify(text):
                    return text.lower().replace(" ", "-").replace(".", "").replace(":", "")

                for line in doc_lines:
                    line = line.strip()
                    
                    # Parse Links [text](url)
                    line = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', line)
                    
                    if line.startswith("# "):
                        html_doc += f"<h1 class='doc-title'>{line[2:]}</h1>"
                    elif line.startswith("## "):
                        title = line[3:]
                        slug = slugify(title)
                        # Check if it's a numbered section like "1. Introducción"
                        if re.match(r'^\d+\.', title):
                             # For TOC links like #1-introducción
                             pass
                        html_doc += f"<h2 id='{slug}' class='doc-section'>{title}</h2>"
                    elif line.startswith("### "):
                        html_doc += f"<h3 class='doc-subsection'>{line[4:]}</h3>"
                    elif line.startswith("* "):
                        html_doc += f"<li class='doc-item'>{line[2:]}</li>"
                    elif line.startswith("!["):
                        # Image parsing: ![alt](url)
                        match = re.search(r'!\[(.*?)\]\((.*?)\)', line)
                        if match:
                            alt, url = match.groups()
                            html_doc += f"<div style='text-align:center; margin: 20px 0;'><img src='{url}' alt='{alt}' style='max-width:100%; border-radius:8px;'></div>"
                    elif line == "---":
                        html_doc += "<hr class='doc-divider'>"
                    elif line.startswith("<div") or line.startswith("</div") or line.startswith("<h3") or line.startswith("<p") or line.startswith("<a"):
                         # Allow raw HTML (for the footer)
                         html_doc += line
                    elif line:
                        # Bold text parsing
                        while "**" in line:
                            line = line.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
                        html_doc += f"<p class='doc-text'>{line}</p>"
                        
                doc_content = html_doc
        except Exception as e:
            doc_content = f"<p>Error loading documentation: {str(e)}</p>"

        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FLUX QUANTUM GAN - Dashboard ({ticker})</title>
    <link rel="icon" href="data:image/png;base64,{img_logo}" type="image/png">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #050810;
            --card-bg: #0c1120;
            --text-color: #f0f4ff;
            --accent-color: #6366f1; /* Indigo FLUX */
            --secondary-accent: #8b5cf6; /* Purple */
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            --border-color: rgba(99, 102, 241, 0.15);
        }}
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 15px;
            background-image: radial-gradient(circle at 50% 0%, #0c1120 0%, #050810 80%);
            font-size: 14px; /* Reduced base font size */
            line-height: 1.5;
        }}
        .container {{
            max_width: 1200px; /* Reduced width */
            margin: 0 auto;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 15px;
        }}
        .brand-area {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        .logo {{
            height: 45px; /* Smaller logo */
            width: auto;
            object-fit: contain;
            filter: drop-shadow(0 0 8px rgba(99, 102, 241, 0.4));
        }}
        h1 {{ 
            margin: 0; 
            color: var(--text-color); 
            font-weight: 700;
            letter-spacing: -0.5px;
            font-size: 1.4rem; /* Smaller title */
            text-transform: uppercase;
        }}
        .subtitle {{
            color: #888;
            font-size: 0.8rem;
            margin-top: 2px;
            transform: translateY(-2px);
            border-color: var(--accent-color);
        }}
        
        .metrics-grid {{
            display: grid !important;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) !important;
            gap: 15px !important;
            margin-bottom: 25px !important;
        }}
        .card {{
            background-color: var(--card-bg) !important;
            border-radius: 8px !important;
            padding: 15px !important;
            border: 1px solid var(--border-color) !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            transition: transform 0.2s ease;
            display: block !important;
        }}
        .card:hover {{
            transform: translateY(-2px);
            border-color: var(--accent-color) !important;
        }}
        .metric-value {{
            font-size: 1.6em !important;
            font-weight: 700 !important;
            margin: 5px 0 !important;
            /* background: linear-gradient(45deg, #fff, #ccc); REMOVED to allow inline colors */
            /* -webkit-background-clip: text; */
            /* -webkit-text-fill-color: transparent; */
            display: block !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3); /* Added for better visibility */
        }}
        .metric-label {{
            color: #9ca3af !important;
            font-size: 0.75em !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            display: block !important;
        }}

        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .grid-3 {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }}
        
        /* Responsive Media Queries */
        @media (max-width: 1024px) {{
            .grid-3 {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        @media (max-width: 768px) {{
            .grid-2, .grid-3 {{ grid-template-columns: 1fr; }}
        }}

        /* Zoomable Images */
        .chart-container {{
            position: relative;
            cursor: pointer;
            overflow: hidden;
            border-radius: 6px;
            border: 1px solid #333;
            height: 220px; /* Reduced height for compact view */
            display: flex;
            align-items: center;
            justify-content: center;
            background: #13131a; /* Match plot background */
        }}
        .chart-container img {{
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain; /* Prevent deformation */
            transition: transform 0.3s ease;
            display: block;
        }}
        .chart-container:hover img {{
            transform: scale(1.05);
        }}
        .zoom-hint {{
            position: absolute;
            top: 8px;
            right: 8px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.7em;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
        }}
        .chart-container:hover .zoom-hint {{
            opacity: 1;
        }}
        
        /* Chart Guides */
        .chart-guide {{
            margin-top: 10px;
            padding: 10px;
            background: rgba(255,255,255,0.03);
            border-radius: 6px;
            font-size: 0.8rem;
            color: #aaa;
            line-height: 1.4;
        }}
        .chart-guide strong {{ color: var(--accent-color); }}
        
        /* Lightbox */
        .lightbox {{
            display: none;
            position: fixed;
            z-index: 1000;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.95);
            justify-content: center;
            align-items: center;
            cursor: zoom-out;
        }}
        .lightbox img {{
            max-width: 90%;
            max-height: 90%;
            border: 2px solid var(--accent-color);
            box-shadow: 0 0 30px rgba(251, 191, 36, 0.2);
            object-fit: contain;
        }}
        
        .advice-box {{
            background: linear-gradient(90deg, rgba(251, 191, 36, 0.05) 0%, rgba(10, 10, 15, 0) 100%);
            border-left: 3px solid var(--accent-color);
            padding: 15px;
            margin-bottom: 30px;
            border-radius: 0 8px 8px 0;
        }}
        .advice-box h3 {{
            color: var(--accent-color);
            margin-top: 0;
            font-size: 1rem;
        }}
        .advice-box p {{ margin: 5px 0 0; font-size: 0.9rem; }}
        
        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin-top: 10px;
            font-size: 0.85rem;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #333;
        }}
        th {{
            background-color: rgba(255,255,255,0.03);
            color: var(--accent-color);
            font-weight: 600;
            font-size: 0.85em;
        }}
        tr:last-child td {{ border-bottom: none; }}
        
        /* Badges */
        .badge {{
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.75em;
            text-transform: uppercase;
            display: inline-block;
        }}
        .badge-buy {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
        .badge-sell {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
        .badge-hold {{ background: rgba(107, 114, 128, 0.2); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.3); }}

        .evolution-gallery {{
            display: flex;
            overflow-x: auto;
            gap: 15px;
            padding-bottom: 15px;
            scrollbar-width: thin;
            scrollbar-color: var(--accent-color) var(--bg-color);
        }}
        .evolution-item {{
            min-width: 280px; /* Smaller items */
            flex: 1;
        }}
        .asset-badge {{
            background: rgba(251, 191, 36, 0.1);
            color: var(--accent-color);
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.7em;
            border: 1px solid rgba(251, 191, 36, 0.3);
            vertical-align: middle;
        }}
        
        /* Documentation Modal */
        .doc-modal {{
            display: none;
            position: fixed;
            z-index: 999;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.9);
            justify-content: center;
            align-items: center;
        }}
        .doc-content {{
            background-color: var(--card-bg);
            width: 80%;
            max-width: 900px;
            height: 85%;
            border-radius: 12px;
            border: 1px solid var(--accent-color);
            padding: 40px;
            overflow-y: auto;
            position: relative;
            box-shadow: 0 0 50px rgba(251, 191, 36, 0.1);
        }}
        .close-doc {{
            position: absolute;
            top: 20px;
            right: 20px;
            color: #fff;
            font-size: 24px;
            cursor: pointer;
            background: none;
            border: none;
        }}
        .doc-btn {{
            background: transparent;
            border: 1px solid var(--accent-color);
            color: var(--accent-color);
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-family: 'Inter', sans-serif;
            font-size: 0.9em;
            transition: all 0.3s;
        }}
        .doc-btn:hover {{
            background: var(--accent-color);
            color: #000;
        }}
        
        /* Doc Styling */
        .doc-title {{ color: var(--accent-color); border-bottom: 1px solid #333; padding-bottom: 10px; }}
        .doc-section {{ color: #fff; margin-top: 30px; }}
        .doc-subsection {{ color: #ccc; font-size: 1.1em; }}
        .doc-text {{ color: #aaa; line-height: 1.6; }}
        .doc-item {{ color: #aaa; margin-left: 20px; margin-bottom: 5px; }}
        .doc-divider {{ border-color: #333; margin: 30px 0; }}
        
        footer {{
            margin-top: auto;
            padding-top: 30px;
            border-top: 1px solid #333;
            text-align: center;
            color: #666;
            font-size: 0.8em;
        }}
    </style>
</head>
<body>
    <!-- Lightbox -->
    <div id="lightbox" class="lightbox" onclick="closeLightbox()">
        <img id="lightbox-img" src="" alt="Zoomed Image">
    </div>
    
    <!-- Documentation Modal -->
    <div id="doc-modal" class="doc-modal">
        <div class="doc-content">
            <button class="close-doc" onclick="closeDoc()">×</button>
            {doc_content}
        </div>
    </div>

    <div class="container">
        <header>
            <div class="brand-area">
                {f'<img src="data:image/png;base64,{img_logo}" alt="Logo" class="logo">' if img_logo else '<svg class="logo" viewBox="0 0 100 100" style="height: 45px; width: 45px; filter: drop-shadow(0 0 8px rgba(99, 102, 241, 0.5));"><polygon points="20,20 80,20 80,40 50,40 50,60 70,60 70,80 30,80 30,50 60,50 60,30 20,30" fill="#6366f1"/></svg>'}
                <div>
                    <h1>FLUX QUANTUM GAN <span style="font-size: 0.5em; color: #666; vertical-align: middle;">(Gen: {datetime.now().strftime('%H:%M:%S')})</span></h1>
                    <div class="subtitle">SISTEMA DE PREDICCIÓN DE ACTIVOS CON IA — FLUX QUANT</div>
                </div>
            </div>
            <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 10px;">
                <div>
                    <h2 style="margin:0; font-size: 1.2rem; border:none; padding:0;">{ticker} <span class="asset-badge">{asset_type}</span></h2>
                    <div style="color: #666; font-size: 0.75em; margin-top: 3px;">{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
                </div>
                <button class="doc-btn" onclick="openDoc()">📘 Ver Documentación Técnica</button>
            </div>
        </header>

        <!-- Advice Section -->
        <div class="advice-box">
            <h3>💡 Análisis del Sistema</h3>
            <p>{advice}</p>
        </div>
        
        <!-- Strategy Panel (NEW) -->
        {strategy_html}
        
        <!-- Comparative Analysis Section (NEW) -->
        {comparative_html}

        <!-- Key Metrics -->
        <div class="metrics-grid">
            <div class="card">
                <div class="metric-label">RMSE (Error Puntos)</div>
                <div class="metric-value" style="color: {rmse_color}">{metrics['RMSE']:.4f}</div>
            </div>
            <div class="card">
                <div class="metric-label">Directional Accuracy</div>
                <div class="metric-value" style="color: {acc_color}">{metrics['Accuracy']*100:.2f}%</div>
            </div>
            <div class="card">
                <div class="metric-label">Win Rate (Backtest)</div>
                <div class="metric-value" style="color: var(--success-color)">{backtest_metrics['Win Rate']:.1f}%</div>
            </div>
            <div class="card">
                <div class="metric-label">Retorno Total (Simulado)</div>
                <div class="metric-value">{backtest_metrics['Total Return %']:.2f}%</div>
            </div>
        </div>
        
        <!-- Training Losses & Features Overview (Grouped) -->
        <div class="grid-2" style="margin-bottom: 25px;">
            <div class="card">
                <h3>📉 Convergencia del Entrenamiento (Losses)</h3>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_losses}" alt="Training Losses">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Cómo leerlo:</strong> Muestra cómo disminuye el error del Generador (G) y Discriminador (D) a lo largo del tiempo.<br>
                    <strong>Interpretación:</strong> Buscamos estabilidad y convergencia hacia cero (o un equilibrio en GANs). Picos repentinos pueden indicar inestabilidad.
                </div>
            </div>

            <div class="card">
                <h3>🔎 Resumen de Features (Inputs)</h3>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_features_overview}" alt="Features Overview">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Cómo leerlo:</strong> Visualización de todas las variables de entrada normalizadas.<br>
                    <strong>Interpretación:</strong> Permite detectar anomalías o patrones en los datos crudos antes de entrar al modelo.
                </div>
            </div>
        </div>

        <!-- Evolution Gallery -->
        <h2>🧬 Evolución del Aprendizaje (Time Travel)</h2>
        <div class="evolution-gallery">
            <div class="card evolution-item">
                <h4>Epoca 1 (El Inicio)</h4>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_epoch_1}" alt="Epoch 1">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Cómo leerlo:</strong> Ruido inicial generado por la red no entrenada.<br>
                    <strong>Interpretación:</strong> El modelo comienza adivinando aleatoriamente.
                </div>
            </div>
            <div class="card evolution-item">
                <h4>Epoca 50 (Aprendiendo)</h4>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_epoch_50}" alt="Epoch 50">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Cómo leerlo:</strong> Primeras formas de onda reconocibles.<br>
                    <strong>Interpretación:</strong> La red empieza a captar la volatilidad básica.
                </div>
            </div>
            <div class="card evolution-item">
                <h4>Epoca 200 (Madurez)</h4>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_epoch_200}" alt="Epoch 200">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Cómo leerlo:</strong> Ajuste fino a los datos reales.<br>
                    <strong>Interpretación:</strong> El modelo refina los detalles y reduce el error.
                </div>
            </div>
            <div class="card evolution-item">
                <h4>Resultado Final</h4>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_final}" alt="Final">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Cómo leerlo:</strong> Predicción final optimizada.<br>
                    <strong>Interpretación:</strong> La mejor estimación posible del modelo actual.
                </div>
            </div>
        </div>

        <!-- Main Analysis Grid -->
        <div class="grid-3" style="margin-top: 20px;">
            <div class="card">
                <h3>🔗 Matriz de Correlación</h3>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_correlation}" alt="Correlation Matrix">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Interpretación:</strong><br>
                    <span style="color: #10b981;">🟢 +1.0 (Verde):</span> Se mueven juntos (Confirmación).<br>
                    <span style="color: #ef4444;">🔴 -1.0 (Rojo):</span> Se mueven opuestos (Cobertura).<br>
                    <span style="color: #fbbf24;">⚠️ VIX Negativo:</span> Si VIX sube, tu activo baja.
                </div>
            </div>
            <div class="card">
                <h3>🔮 Gaussian Process</h3>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_gpr}" alt="Gaussian Process">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Interpretación:</strong> Zona naranja = Intervalo de confianza (95%).
                </div>
            </div>
            <div class="card">
                <h3>📈 Proyección ARIMA</h3>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_arima}" alt="ARIMA Forecast">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Interpretación:</strong> Tendencia estadística pura.
                </div>
            </div>
        </div>

        <!-- Technical Dashboard (Full Width Section) -->
        <section style="width: 100%; display: block; margin: 30px 0; clear: both;">
            <div class="card">
                <h3>📊 Dashboard Técnico</h3>
                <div class="chart-container" style="height: 400px;" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_dashboard}" alt="Technical Dashboard">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Interpretación:</strong> Cruces de medias y MACD.
                </div>
            </div>
        </section>

        <div class="grid-3" style="margin-top: 20px;">
            <div class="card">
                <h3>😨 Sentimiento (VIX)</h3>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_sentiment}" alt="Sentiment">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Interpretación:</strong> Picos de miedo = Oportunidad de compra.
                </div>
            </div>
            <div class="card">
                <h3>🧠 Feature Importance</h3>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_features}" alt="Feature Importance">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Interpretación:</strong> Qué indicadores pesan más.
                </div>
            </div>
            <div class="card">
                <h3>🌊 Ciclos (Fourier)</h3>
                <div class="chart-container" onclick="openLightbox(this)">
                    <img src="data:image/png;base64,{img_fourier}" alt="Fourier Analysis">
                    <div class="zoom-hint">🔍 Click to Zoom</div>
                </div>
                <div class="chart-guide">
                    <strong>Interpretación:</strong> Ciclos ocultos del mercado.
                </div>
            </div>
        </div>
        
        <!-- Backtesting Signals -->
        <div class="card" style="margin-top: 25px;">
            <h3>📡 Últimas Señales de Trading (Simulación)</h3>
            <p style="font-size: 0.85rem; color: #888;">Registro de las últimas decisiones tomadas por el sistema.</p>
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Precio Real</th>
                        <th>Predicción</th>
                        <th>Señal</th>
                        <th>Posición</th>
                    </tr>
                </thead>
                <tbody>
                    {signals_html}
                </tbody>
            </table>
        </div>
        
        <footer>
            <p>&copy; {datetime.now().year} QUANTUM GAN System. Powered by <a href="https://llamaia.nbmsystemas.com/" style="color: var(--accent-color); text-decoration: none;">NBM Systems</a>.</p>
            <p style="font-size: 0.8em; opacity: 0.7;">Disclaimer: This system is for educational and research purposes only. Trading futures and crypto involves significant risk.</p>
        </footer>

    </div>
    
    <script>
        function openLightbox(element) {{
            const img = element.querySelector('img');
            const lightbox = document.getElementById('lightbox');
            const lightboxImg = document.getElementById('lightbox-img');
            lightboxImg.src = img.src;
            lightbox.style.display = 'flex';
        }}
        
        function closeLightbox() {{
            document.getElementById('lightbox').style.display = 'none';
        }}
        
        function openDoc() {{
            document.getElementById('doc-modal').style.display = 'flex';
        }}
        
        function closeDoc() {{
            document.getElementById('doc-modal').style.display = 'none';
        }}
        
        // Close modal on outside click
        window.onclick = function(event) {{
            const modal = document.getElementById('doc-modal');
            if (event.target == modal) {{
                modal.style.display = "none";
            }}
        }}
    </script>
</body>
</html>
"""
        
        with open(self.html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        return self.html_path
