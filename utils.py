import os
import glob
from config import AOI_DIR

def find_shapefiles():
    """
    Encontra todos os arquivos .shp na pasta AOI_DIR.
    Retorna uma lista de caminhos completos.
    """
    search_path = os.path.join(AOI_DIR, '*.shp')
    shapefiles = glob.glob(search_path)
    if not shapefiles:
        print(f"Atenção: Nenhum arquivo .shp encontrado em {AOI_DIR}")
        print("Por favor, adicione seus shapefiles de AOI nesta pasta.")
    return shapefiles