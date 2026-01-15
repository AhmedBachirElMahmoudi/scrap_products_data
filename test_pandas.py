print("Start")
import pandas as pd
print("Pandas imported")
try:
    df = pd.read_excel("BACHIR CODES.xlsx")
    print(df.columns)
except Exception as e:
    print(e)
print("Done")
