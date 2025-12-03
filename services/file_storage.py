# services/file_storage.py
import os
import uuid
from pathlib import Path
import shutil

# Pasta onde as imagens serão salvas (dentro da pasta do projeto)
# Certifique-se de que a pasta 'static' e 'images' existem
IMAGE_DIR = Path(os.getcwd()) / "static" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True) # Garante que a pasta existe

def save_image_locally(file_path: str, file_name: str) -> str:
    """
    Salva o arquivo temporário do Flet no diretório estático e retorna a URL relativa.
    
    :param file_path: Caminho temporário do arquivo (fornecido pelo Flet FilePicker).
    :param file_name: Nome original do arquivo.
    :return: URL relativa da imagem salva (ex: 'static/images/abcdefg.png').
    """
    if not file_path:
        return None
        
    try:
        # Gera um nome de arquivo único para evitar colisões
        extension = Path(file_name).suffix.lower()
        if extension not in ['.jpg', '.jpeg', '.png', '.gif']:
            # Opcional: Adicionar validação de extensão aqui
            return None 
            
        unique_filename = f"{uuid.uuid4()}{extension}"
        target_path = IMAGE_DIR / unique_filename
        
        # Copia o arquivo do caminho temporário para o destino permanente
        shutil.copyfile(file_path, target_path)

        # Retorna o caminho relativo (URL) que será usado no banco de dados e no front-end
        return f"static/images/{unique_filename}"
        
    except Exception as e:
        print(f"Erro ao salvar arquivo localmente: {e}")
        return None