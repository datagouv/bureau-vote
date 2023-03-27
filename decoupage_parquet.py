import pandas as pd
import os

path_in = r"C:\Users\Dinum\Documents\Projets\Elections\work\table_adresses.parquet"
df = pd.read_parquet(path_in)
df['dep_bv'] = df['code_commune_ref'].apply(lambda s: s[:3] if s[:2]=='97' else s[:2])

for k in df.dep_bv.unique():
    print(k)
    path_out = f"parquet/table_{k}.parquet"
    if f"table_{k}.parquet" in os.listdir("parquet/"):
        print('Already processed')
    else:
        df[df.dep_bv == k].to_parquet(path_out)
