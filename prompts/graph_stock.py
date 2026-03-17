import argparse
import matplotlib.pyplot as plt
import qlib
from qlib.data import D
from qlib.config import REG_US

def main():
    parser = argparse.ArgumentParser(description="Genera una gráfica de evolución de una acción usando datos de Qlib.")
    parser.add_argument("ticker", type=str, help="El ticker de la acción (por ejemplo, AAPL)")
    args = parser.parse_args()

    # Inicializar Qlib con los datos de mercado de US
    # Nota: provider_uri debe apuntar a donde tengas descargados los datos de Qlib.
    provider_uri = '~/.qlib/qlib_data/us_data'
    try:
        qlib.init(provider_uri=provider_uri, region=REG_US)
    except Exception as e:
        print(f"Aviso al inicializar Qlib: {e}")

    ticker = args.ticker.upper()
    start_date = "2020-01-01"

    print(f"Recuperando datos para {ticker} desde {start_date}...")

    # Recuperar el precio de cierre ($close) de la acción
    instruments = [ticker]
    fields = ['$close']
    try:
        df = D.features(instruments, fields, start_time=start_date)
    except Exception as e:
        print(f"Error al recuperar datos: {e}")
        return

    if df is None or df.empty:
        print(f"No se encontraron datos para el ticker {ticker} desde {start_date}.")
        return

    # Qlib devuelve un DataFrame con MultiIndex (instrument, datetime).
    # Seleccionamos solo los datos del ticker especificado para graficar con normalidad.
    df_ticker = df.loc[ticker]

    # Crear la gráfica
    plt.figure(figsize=(12, 6))
    plt.plot(df_ticker.index, df_ticker['$close'], label=f'Precio de Cierre de {ticker}', color='#1f77b4')
    
    plt.title(f'Evolución del valor de {ticker} desde el {start_date}')
    plt.xlabel('Fecha')
    plt.ylabel('Precio ($)')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()

    # Mostrar la gráfica por pantalla
    plt.show()

if __name__ == "__main__":
    main()
