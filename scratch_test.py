import sys
sys.path.append('.')

from core.data_provider import DataProvider
from analysis.quant import order_flow_approximation

dp = DataProvider()
df, info = dp.fetch('BTC-USD', '1d', '1mo', force_refresh=True)

print(f"INFO: {info}")
print(f"Columns: {df.columns.tolist()}")

of = order_flow_approximation(df)
print(f"Order Flow Result: {of}")
