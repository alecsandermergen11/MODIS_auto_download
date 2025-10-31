import questionary
import sys
import os
from datetime import datetime
from tqdm import tqdm
from config import RAW_TIF_DIR, CSV_DIR
from config import setup_directories
from utils import find_shapefiles
from gee_ops import (
    authenticate_gee, 
    get_aoi_geometry, 
    process_collection, 
    MODIS_COLLECTIONS
)

def main():
    """Função principal da ferramenta de download interativa."""
    
    print("=============================================")
    print("  Ferramenta de Download de Dados MODIS GEE  ")
    print("=============================================")

    # --- 1. Setup: Criar pastas e autenticar ---
    setup_directories()
    authenticate_gee()

    # --- 2. Selecionar AOIs ---
    shapefiles = find_shapefiles()
    if not shapefiles:
        sys.exit(1) 

    selected_aoi_basenames = questionary.checkbox(
        "Quais Áreas de Interesse (AOI) você quer usar? (Use ESPAÇO para selecionar)",
        choices=[os.path.basename(shp) for shp in shapefiles]
    ).ask()

    if not selected_aoi_basenames:
        print("Nenhuma AOI selecionada. Saindo.")
        sys.exit(0)

    # --- 3. Selecionar Datas ---
    def is_valid_date(date_str):
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return "Formato inválido. Use AAAA-MM-DD"

    start_date = questionary.text(
        "Digite a data de INÍCIO (AAAA-MM-DD):",
        validate=is_valid_date,
        default='2001-01-01'
    ).ask()

    end_date = questionary.text(
        "Digite a data de FIM (AAAA-MM-DD):",
        validate=is_valid_date,
        default=datetime.now().strftime('%Y-%m-%d')
    ).ask()

    # --- 4. Selecionar Coleções ---
    available_collections = list(MODIS_COLLECTIONS.keys())
    
    selected_collections = questionary.checkbox(
        "Quais coleções MODIS você quer baixar? (Use ESPAÇO para selecionar)",
        choices=available_collections
    ).ask()

    if not selected_collections:
        print("Nenhuma coleção selecionada. Saindo.")
        sys.exit(0)

    # --- 5. Confirmação e Execução ---
    print("\n=== RESUMO DA TAREFA ===")
    print(f"  AOIs a processar: {', '.join(selected_aoi_basenames)}")
    print(f"  Período: {start_date} até {end_date}")
    print(f"  Coleções: {', '.join(selected_collections)}")
    
    confirm = questionary.confirm(
        "Tudo certo? Deseja iniciar o download em lote?",
        default=True
    ).ask()

    if not confirm:
        print("Operação cancelada.")
        sys.exit(0)

    # --- 6. Loop de Processamento (NESTED) ---
    
    for aoi_basename in selected_aoi_basenames:
        print(f"\n\n=======================================================")
        print(f"   Iniciando processamento para a AOI: {aoi_basename} ")
        print(f"=======================================================")
        
        # --- Carregar a geometria para esta AOI específica ---
        aoi_path_full = next(shp for shp in shapefiles if shp.endswith(aoi_basename))
        aoi_name = os.path.splitext(aoi_basename)[0]
        
        try:
            aoi_geom = get_aoi_geometry(aoi_path_full)
            if aoi_geom is None:
                print(f"Erro ao carregar geometria para {aoi_basename}. Pulando esta AOI.")
                continue 
        except Exception as e:
            print(f"Erro fatal ao carregar o shapefile {aoi_basename}: {e}")
            print("Verifique o arquivo e tente novamente. Pulando esta AOI.")
            continue 

        # *** INÍCIO DA MUDANÇA: Adicionar barra de progresso TQDM ***
        # Esta barra mostra o progresso das *coleções* para a AOI atual
        collection_progressbar = tqdm(selected_collections, 
                                      desc=f"Progresso (AOI: {aoi_name})", 
                                      unit="coleção")
        
        for collection_key in collection_progressbar:
            # Atualiza a descrição da barra para a coleção atual
            collection_progressbar.set_postfix_str(collection_key)
            
            try:
                process_collection(aoi_name, collection_key, aoi_geom, start_date, end_date)
            except Exception as e:
                # Se algo der errado, registra e continua
                tqdm.write(f"*** ERRO GERAL ao processar {collection_key} para {aoi_name}: {e}")
                tqdm.write("   Pulando para a próxima coleção...")
        # *** FIM DA MUDANÇA ***
        
        print(f"\n--- Processamento da AOI {aoi_name} concluído ---")

    print("\n\n===================================")
    print("  Processamento de todas as tarefas concluído!  ")
    print(f"  TIFs salvos em: {RAW_TIF_DIR}")
    print(f"  CSVs salvos em: {CSV_DIR}")
    print("===================================")


if __name__ == '__main__':
    main()