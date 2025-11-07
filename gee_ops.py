import ee
import sys
import io
import os
import requests
import zipfile
import pandas as pd
import geopandas as gpd
from config import RAW_TIF_DIR, CSV_DIR
from tqdm import tqdm

# === Garantir UTF-8 no Windows ===
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')

# === DICIONÁRIO EXPANDIDO DE COLEÇÕES MODIS (V6.1) ===
# Mapeia um nome amigável para os detalhes da coleção no GEE
MODIS_COLLECTIONS = {
    # --- Vegetação (NDVI / EVI) ---
    'NDVI_16Day_250m_Terra (MOD13Q1)': {
        'id': 'MODIS/061/MOD13Q1',
        'bands': ['NDVI'],
        'scale_factor': 0.0001,
        'scale_proj': 250
    },
    'EVI_16Day_250m_Terra (MOD13Q1)': {
        'id': 'MODIS/061/MOD13Q1',
        'bands': ['EVI'],
        'scale_factor': 0.0001,
        'scale_proj': 250
    },
    
    # --- Evapotranspiração (ET) ---
    'ET_Evapotranspiration_8Day_500m_Terra (MOD16A2)': {
        'id': 'MODIS/061/MOD16A2',
        'bands': ['ET'],
        'scale_factor': 0.1,
        'scale_proj': 500
    },
    'LE_Latente_heat_flux_ET_8Day_500m_Terra (MOD16A2)': {
        'id': 'MODIS/061/MOD16A2',
        'bands': ['LE'],
        'scale_factor': 10000,
        'scale_proj': 500
    },
    'PET_Potential_ET_8Day_500m_Terra (MOD16A2)': {
        'id': 'MODIS/061/MOD16A2',
        'bands': ['PET'],
        'scale_factor': 0.1,
        'scale_proj': 500
    },

    'ET_Evapotranspiration_8Day_500m_GF_Terra (MOD16A2GF)': {
        'id': 'MODIS/061/MOD16A2GF',
        'bands': ['ET'],
        'scale_factor': 0.1,
        'scale_proj': 500
    },
    'LE_Latente_heat_flux_ET_8Day_500m_GF_Terra (MOD16A2GF)': {
        'id': 'MODIS/061/MOD16A2GF',
        'bands': ['LE'],
        'scale_factor': 10000,
        'scale_proj': 500
    },
    'PET_Potential_ET_8Day_500m_GF_Terra (MOD16A2GF)': {
        'id': 'MODIS/061/MOD16A2GF',
        'bands': ['PET'],
        'scale_factor': 0.1,
        'scale_proj': 500
    },

    # --- Temperatura da Superfície (LST) ---
    'LST_Day_Daily_1km_Terra (MOD11A1)': {
        'id': 'MODIS/061/MOD11A1',
        'bands': ['LST_Day_1km'],
        'scale_factor': 0.02,  # Converte para Kelvin
        'scale_proj': 1000
    },
    'LST_Night_Daily_1km_Terra (MOD11A1)': {
        'id': 'MODIS/061/MOD11A1',
        'bands': ['LST_Night_1km'],
        'scale_factor': 0.02, # Converte para Kelvin
        'scale_proj': 1000
    },

        # --- Temperatura da Superfície (LST) ---
    'LST_Day_8day_1km_Terra (MOD11A2)': {
        'id': 'MODIS/061/MOD11A2',
        'bands': ['LST_Day_1km'],
        'scale_factor': 0.02,  # Converte para Kelvin
        'scale_proj': 1000
    },
    'LST_Night_8day_1km_Terra (MOD11A2)': {
        'id': 'MODIS/061/MOD11A2',
        'bands': ['LST_Night_1km'],
        'scale_factor': 0.02, # Converte para Kelvin
        'scale_proj': 1000
    },

    # --- LAI / FPAR ---
    'LAI_8Day_500m_Terra (MOD15A2H)': {
        'id': 'MODIS/061/MOD15A2H',
        'bands': ['Lai_500m'],
        'scale_factor': 0.1,
        'scale_proj': 500
    },
    'FPAR_8Day_500m_Terra (MOD15A2H)': {
        'id': 'MODIS/061/MOD15A2H',
        'bands': ['Fpar_500m'],
        'scale_factor': 0.01,
        'scale_proj': 500
    },

    'PAR_Daily_3-hours_500m (MCD18C2)': {
        'id': 'MODIS/062/MCD18C2',
        'bands': ['GMT_0000_PAR', 'GMT_0300_PAR', 'GMT_0600_PAR',
                  'GMT_0900_PAR', 'GMT_1200_PAR', 'GMT_1500_PAR',
                  'GMT_1800_PAR', 'GMT_2100_PAR'],
        'scale_factor': 1,
        'scale_proj': 500
    },
    
    # --- Cobertura de Neve ---
    'SnowCover_Daily_500m_Terra (MOD10A1)': {
        'id': 'MODIS/061/MOD10A1',
        'bands': ['NDSI_Snow_Cover'],
        'scale_factor': 1, # É porcentagem
        'scale_proj': 500
    },
    
    # --- Área Queimada ---
    'BurnedArea_Monthly_500m_Terra (MCD64A1)': {
        'id': 'MODIS/061/MCD64A1',
        'bands': ['BurnDate'], # Dia do ano
        'scale_factor': 1,
        'scale_proj': 500
    },
    
    # --- Cobertura da Terra ---
    'LandCover_Type1_Yearly_500m_Terra (MCD12Q1)': {
        'id': 'MODIS/061/MCD12Q1',
        'bands': ['LC_Type1'], # Classificação IGBP
        'scale_factor': 1,
        'scale_proj': 500
    },

    # --- Cobertura da Terra ---
    'Gross_primary_production_GPP_8day_500m_Terra (MOD17A2HGF)': {
        'id': 'MODIS/061/MOD17A2HGF',
        'bands': ['Gpp'], # GPP
        'scale_factor': 0.0001,
        'scale_proj': 500
    },

    'water_mask_250m_Terra (MOD44W)': {
        'id': 'MODIS/006/MOD44W',
        'bands': ['water_mask'], # GPP
        'scale_factor': 1,
        'scale_proj': 250
    },
    # --- Vegetação (NDVI / EVI) ---
    'NDVI_16Day_250m_Aqua (MYD13Q1)': {
        'id': 'MODIS/061/MYD13Q1',
        'bands': ['NDVI'],
        'scale_factor': 0.0001,
        'scale_proj': 250
    },
    'EVI_16Day_250m_Aqua (MYD13Q1)': {
        'id': 'MODIS/061/MYD13Q1',
        'bands': ['EVI'],
        'scale_factor': 0.0001,
        'scale_proj': 250
    },
    
    # --- Evapotranspiração (ET) ---
    'ET_Evapotranspiration_8Day_500m_Aqua (MYD16A2)': {
        'id': 'MODIS/061/MYD16A2',
        'bands': ['ET'],
        'scale_factor': 0.1,
        'scale_proj': 500
    },
    'LE_Latente_heat_flux_ET_8Day_500m_Aqua (MYD16A2)': {
        'id': 'MODIS/061/MYD16A2',
        'bands': ['LE'],
        'scale_factor': 10000,
        'scale_proj': 500
    },
    'PET_Potential_ET_8Day_500m_Aqua (MYD16A2)': {
        'id': 'MODIS/061/MYD16A2',
        'bands': ['PET'],
        'scale_factor': 0.1,
        'scale_proj': 500
    },

    # --- Temperatura da Superfície (LST) ---
    'LST_Day_Daily_1km_Aqua (MYD11A1)': {
        'id': 'MODIS/061/MYD11A1',
        'bands': ['LST_Day_1km'],
        'scale_factor': 0.02,  # Converte para Kelvin
        'scale_proj': 1000
    },
    'LST_Night_Daily_1km_Aqua (MYD11A1)': {
        'id': 'MODIS/061/MYD11A1',
        'bands': ['LST_Night_1km'],
        'scale_factor': 0.02, # Converte para Kelvin
        'scale_proj': 1000
    },

        # --- Temperatura da Superfície (LST) ---
    'LST_Day_8day_1km_Aqua (MYD11A2)': {
        'id': 'MODIS/061/MYD11A2',
        'bands': ['LST_Day_1km'],
        'scale_factor': 0.02,  # Converte para Kelvin
        'scale_proj': 1000
    },
    'LST_Night_8day_1km_Aqua (MYD11A2)': {
        'id': 'MODIS/061/MYD11A2',
        'bands': ['LST_Night_1km'],
        'scale_factor': 0.02, # Converte para Kelvin
        'scale_proj': 1000
    },

    # --- LAI / FPAR ---
    'LAI_8Day_500m_Aqua (MYD15A2H)': {
        'id': 'MODIS/061/MYD15A2H',
        'bands': ['Lai_500m'],
        'scale_factor': 0.1,
        'scale_proj': 500
    },
    'FPAR_8Day_500m_Aqua (MYD15A2H)': {
        'id': 'MODIS/061/MYD15A2H',
        'bands': ['Fpar_500m'],
        'scale_factor': 0.01,
        'scale_proj': 500
    },
    
    # --- Cobertura de Neve ---
    'SnowCover_Daily_500m_Aqua (MYD10A1)': {
        'id': 'MODIS/061/MYD10A1',
        'bands': ['NDSI_Snow_Cover'],
        'scale_factor': 1, # É porcentagem
        'scale_proj': 500
    },

    # --- Cobertura da Terra ---
    'Gross_primary_production_GPP_8day_500m_Aqua (MYD17A2H)': {
        'id': 'MODIS/061/MYD17A2H',
        'bands': ['Gpp'], # GPP
        'scale_factor': 0.0001,
        'scale_proj': 500
    },

}


def authenticate_gee():
    """Inicializa ou autentica no Google Earth Engine."""
    try:
        ee.Initialize(project='ee-alecsanderndvi') # Tenta usar seu projeto
        # print("GEE inicializado com sucesso.") # <--- Silenciado para um log mais limpo
    except Exception:
        try:
            print("Autenticando no Google Earth Engine...")
            ee.Authenticate()
            ee.Initialize(project='ee-alecsanderndvi')
            print("GEE inicializado com sucesso.")
        except Exception as e:
            print(f"Erro ao inicializar o GEE: {e}")
            print("Verifique sua conexão e configuração do GEE.")
            sys.exit(1)


def get_aoi_geometry(shapefile_path):
    """
    Lê um shapefile, dissolve em uma única geometria e converte para ee.Geometry.
    """
    print(f"Carregando AOI de: {shapefile_path}")
    gdf = gpd.read_file(shapefile_path)
    
    # Reprojeta para WGS84 (EPSG:4326) se necessário, que é o padrão do GEE
    if gdf.crs.to_epsg() != 4326:
        print("Reprojetando AOI para EPSG:4326...")
        gdf = gdf.to_crs(epsg=4326)
        
    # Dissolve todas as feições em uma única
    gdf_union = gdf.unary_union
    
    # Converte para GeoJSON (dicionário)
    gjson = gdf_union.__geo_interface__
    
    # Cria a geometria do GEE
    if gjson['type'] == 'Polygon':
        aoi_geom = ee.Geometry.Polygon(gjson['coordinates'])
    elif gjson['type'] == 'MultiPolygon':
        aoi_geom = ee.Geometry.MultiPolygon(gjson['coordinates'])
    else:
        print(f"Tipo de geometria não suportado: {gjson['type']}")
        return None
        
    print("Geometria AOI carregada no GEE.")
    return aoi_geom


def process_collection(aoi_name, collection_key, aoi_geom, start_date, end_date):
    """
    Processa uma única coleção: baixa todos os TIFs e gera um CSV de médias.
    """
    collection_info = MODIS_COLLECTIONS[collection_key]
    
    collection_id = collection_info['id']
    bands = collection_info['bands']
    scale_factor = collection_info.get('scale_factor', 1.0)
    scale_proj = collection_info['scale_proj']
    
    # Não vamos mais imprimir isso, a barra de progresso principal mostra
    # print(f"\n--- Iniciando processamento para: {collection_key} [AOI: {aoi_name}] ---")
    
    # --- 1. Criar pastas de saída específicas ---
    tif_output_dir = os.path.join(RAW_TIF_DIR, aoi_name, collection_key)
    csv_output_dir = os.path.join(CSV_DIR, aoi_name)
    os.makedirs(tif_output_dir, exist_ok=True)
    os.makedirs(csv_output_dir, exist_ok=True)
    
    # --- 2. Consultar a coleção ---
    collection = (
        ee.ImageCollection(collection_id)
        .filterDate(start_date, end_date)
        .filterBounds(aoi_geom)
        .select(bands)
    )

    if scale_factor != 1.0:
        collection = collection.map(
            lambda img: img.multiply(scale_factor)
                         .copyProperties(img, img.propertyNames())
        )

    # --- 3. Obter o tamanho da coleção ANTES de criar a lista ---
    total_images = collection.size().getInfo()
    
    if total_images == 0:
        # Escreve a informação sem quebrar a barra de progresso
        tqdm.write(f"[{collection_key}] Nenhuma imagem encontrada para este período/região.")
        mean_data_list = []
    else:
        # print(f"Total de imagens encontradas: {total_images}") # <-- Substituído pela barra
        
        # --- 4. Iterar e baixar imagens ---
        image_list = collection.toList(total_images)
        mean_data_list = [] 

        # *** Adiciona a barra de progresso TQDM para imagens ***
        # 'leave=False' faz a barra desaparecer após a conclusão
        # 'unit="img"' apenas muda o texto da unidade
        image_progressbar = tqdm(range(total_images), 
                                 desc="Imagens", 
                                 unit="img", 
                                 leave=False) 
        
        for i in image_progressbar:
            image = ee.Image(image_list.get(i))
            date_str = image.date().format('YYYY-MM-dd').getInfo()
            
            # Atualiza a barra com a data da imagem atual
            image_progressbar.set_postfix_str(date_str) 
            
            name_prefix = f"{collection_key}_{date_str}"
            
            # --- 4a. Download do GeoTIFF ---
            tif_path = os.path.join(tif_output_dir, f"{name_prefix}.tif")
            
            if os.path.exists(tif_path):
                # Usamos tqdm.write() para não quebrar a barra
                tqdm.write(f"  [OK] Já existe: {name_prefix}.tif")
            else:
                # Não precisamos de print, a barra mostra o progresso
                # print(f"[{i+1}/{total_images}] Baixando: {name_prefix}.tif")
                temp_download_path = None 
                try:
                    image_clipped = image.clip(aoi_geom).reproject(crs='EPSG:4326', scale=scale_proj)
                    url = image_clipped.getDownloadURL({
                        'name': name_prefix, 'scale': scale_proj, 'region': aoi_geom, 'format': 'GEO_TIFF'
                    })
                    
                    r = requests.get(url, stream=True)
                    r.raise_for_status()
                    
                    temp_download_path = os.path.join(tif_output_dir, f"{name_prefix}.temp_download")
                    with open(temp_download_path, 'wb') as f:
                        f.write(r.content)
                    
                    if zipfile.is_zipfile(temp_download_path):
                        with zipfile.ZipFile(temp_download_path, 'r') as z:
                            for file in z.namelist():
                                if file.lower().endswith('.tif'):
                                    extracted_file_path = z.extract(file, tif_output_dir)
                                    if os.path.exists(tif_path): os.remove(tif_path)
                                    os.rename(extracted_file_path, tif_path)
                                    # tqdm.write(f"  [ZIP] Salvo: {tif_path}") # <-- Opcional, pode poluir
                                    break 
                        os.remove(temp_download_path)
                    
                    else:
                        os.rename(temp_download_path, tif_path)
                        # tqdm.write(f"  [TIF] Salvo: {tif_path}") # <-- Opcional

                except Exception as e:
                    # Garantir que erros sejam impressos com tqdm.write
                    tqdm.write(f"   *** ERRO ao baixar {name_prefix}: {e}")
                    if temp_download_path and os.path.exists(temp_download_path):
                        os.remove(temp_download_path)
                    if "computation timed out" in str(e).lower():
                        tqdm.write("   *** Dica: Sua AOI pode ser muito complexa. Tente simplificá-la.")
                    continue 

            # --- 4b. Calcular Média para o CSV ---
            try:
                mean_dict = image.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=aoi_geom, scale=scale_proj, maxPixels=1e10
                ).getInfo() 
                
                row = {'date': date_str}
                for band in bands:
                    row[band] = mean_dict.get(band)
                mean_data_list.append(row)
                
            except Exception as e:
                tqdm.write(f"   *** ERRO ao calcular média para {name_prefix}: {e}")
    
    # --- 5. Salvar o CSV de médias ---
    if mean_data_list: 
        csv_filename = f"{collection_key.split(' ')[0]}_means.csv"
        csv_path = os.path.join(csv_output_dir, csv_filename)
        
        df = pd.DataFrame(mean_data_list)
        df = df.sort_values(by='date')
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        # Usamos print aqui, pois as barras de progresso internas já terminaram
        print(f"  ✅ CSV com médias salvo em: {csv_path}")
    
    # Não precisamos de print de conclusão aqui, a barra principal cuida disso
    # print(f"--- Processamento de {collection_key} concluído ---")