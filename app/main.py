# app/main.py
import os
import re
import argparse
from ebooklib import epub
import openai
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

def main(text_file, output_file, api_key=None):
    # Configurar la API de OpenAI
    if api_key:
        openai.api_key = api_key
    else:
        openai.api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai.api_key:
        raise ValueError("Se requiere una clave API de OpenAI")
    
    # Leer el texto completo
    with open(text_file, 'r', encoding='utf-8') as file:
        raw_text = file.read()
    
    print(f"Texto cargado: {len(raw_text)} caracteres")
    
    # Procesar con IA para estructurar
    print("Procesando texto con IA...")
    book_structure = process_with_ai(raw_text)
    
    # Crear EPUB
    print("Generando archivo EPUB...")
    create_epub(book_structure, output_file)
    
    print(f"EPUB creado exitosamente: {output_file}")

def process_with_ai(text):
    """Procesa el texto usando IA para identificar capítulos y estructura"""
    # Primera pasada - Identificar título, autor y estructura general
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Analiza este texto y extrae: título del libro, autor (si se menciona), y una estructura de capítulos propuesta. Si no hay capítulos claros, sugiere una división lógica."},
            {"role": "user", "content": text[:4000]}  # Primeras 4000 caracteres para análisis inicial
        ]
    )
    
    initial_analysis = response.choices[0].message.content
    
    # Determinar número aproximado de capítulos basado en longitud
    estimated_chapters = max(5, len(text) // 20000)
    
    # Segunda pasada - Procesar el texto completo por secciones
    chunk_size = 10000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    processed_structure = {
        "title": "",
        "author": "",
        "chapters": []
    }
    
    # Extraer título y autor del análisis inicial
    # (Código simplificado, en la implementación real sería más robusto)
    if "Título:" in initial_analysis:
        title_match = re.search(r"Título: (.+)", initial_analysis)
        if title_match:
            processed_structure["title"] = title_match.group(1)
    
    if "Autor:" in initial_analysis:
        author_match = re.search(r"Autor: (.+)", initial_analysis)
        if author_match:
            processed_structure["author"] = author_match.group(1)
    
    # Procesar cada sección del texto
    current_chapter = {"title": "", "content": []}
    
    for i, chunk in enumerate(chunks):
        print(f"Procesando fragmento {i+1}/{len(chunks)}...")
        prompt = f"Este es un fragmento de texto de un libro. Identifica si hay un nuevo capítulo, y estructura el texto en párrafos coherentes. Si detectas el inicio de un nuevo capítulo, indícalo claramente con 'NUEVO CAPÍTULO: [título]'. Fragmento: {chunk}"
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Eres un asistente especializado en formato de libros."},
                {"role": "user", "content": prompt}
            ]
        )
        
        processed_chunk = response.choices[0].message.content
        
        # Verificar si hay un nuevo capítulo en este fragmento
        if "NUEVO CAPÍTULO:" in processed_chunk:
            # Si ya teníamos un capítulo en proceso, lo guardamos
            if current_chapter["title"] or current_chapter["content"]:
                processed_structure["chapters"].append(current_chapter)
            
            # Extraer el título del nuevo capítulo
            chapter_match = re.search(r"NUEVO CAPÍTULO: (.+)", processed_chunk)
            chapter_title = chapter_match.group(1) if chapter_match else f"Capítulo {len(processed_structure['chapters'])+1}"
            processed_chunk = re.sub(r"NUEVO CAPÍTULO: .+", "", processed_chunk).strip()
            
            current_chapter = {"title": chapter_title, "content": [processed_chunk]}
        else:
            current_chapter["content"].append(processed_chunk)
    
    # Añadir el último capítulo
    if current_chapter["title"] or current_chapter["content"]:
        processed_structure["chapters"].append(current_chapter)
    
    # Si no se detectaron capítulos, crear uno general
    if not processed_structure["chapters"]:
        processed_structure["chapters"] = [{"title": "Libro completo", "content": [text]}]
    
    return processed_structure

def create_epub(book_structure, output_file):
    """Crea un archivo EPUB a partir de la estructura del libro"""
    book = epub.EpubBook()
    
    # Configurar metadatos
    book.set_title(book_structure["title"] or "Libro sin título")
    if book_structure["author"]:
        book.add_author(book_structure["author"])
    
    chapters = []
    toc = []
    
    # Crear capítulos
    for i, chapter in enumerate(book_structure["chapters"]):
        chapter_title = chapter["title"] or f"Capítulo {i+1}"
        chapter_content = "\n\n".join(chapter["content"])
        
        # Crear el objeto capítulo
        epub_chapter = epub.EpubHtml(
            title=chapter_title,
            file_name=f'chapter_{i+1}.xhtml',
            lang='es'
        )
        
        # Formatear el contenido HTML
        chapter_html = f"<h1>{chapter_title}</h1>"
        
        # Convertir párrafos
        paragraphs = chapter_content.split("\n\n")
        for paragraph in paragraphs:
            if paragraph.strip():
                # Reemplazar saltos de línea simples con espacios
                paragraph = re.sub(r'(?<!\n)\n(?!\n)', ' ', paragraph)
                chapter_html += f"<p>{paragraph.strip()}</p>"
        
        epub_chapter.content = chapter_html
        book.add_item(epub_chapter)
        
        chapters.append(epub_chapter)
        toc.append(epub.Link(f'chapter_{i+1}.xhtml', chapter_title, f'chapter_{i+1}'))
    
    # Agregar CSS
    style = """
    body {
        font-family: Times New Roman, serif;
        margin: 5%;
        text-align: justify;
    }
    h1 {
        text-align: center;
        margin-bottom: 1em;
    }
    p {
        text-indent: 1.5em;
        margin-top: 0.5em;
        margin-bottom: 0.5em;
        line-height: 1.5;
    }
    """
    
    default_css = epub.EpubItem(
        uid="style_default",
        file_name="style/default.css",
        media_type="text/css",
        content=style
    )
    book.add_item(default_css)
    
    # Configurar la espina dorsal del libro
    book.spine = ['nav'] + chapters
    
    # Agregar tabla de contenidos
    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Escribir el archivo EPUB
    epub.write_epub(output_file, book, {})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convertir texto a EPUB usando IA')
    parser.add_argument('--input', required=True, help='Archivo de texto de entrada')
    parser.add_argument('--output', required=True, help='Nombre del archivo EPUB de salida')
    parser.add_argument('--api-key', help='Clave API de OpenAI (opcional, también se puede usar variable de entorno)')
    
    args = parser.parse_args()
    main(args.input, args.output, args.api_key)