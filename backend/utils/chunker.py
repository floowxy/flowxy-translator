"""
Text Chunker - Divide texto en chunks respetando oraciones
"""
import re
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class TextChunker:
    """Divide texto en chunks inteligentes"""
    
    def __init__(
        self,
        max_length: int = 512,
        overlap: int = 50,
        respect_sentences: bool = True,
    ):
        """
        Args:
            max_length: Longitud máxima de cada chunk (en caracteres)
            overlap: Cantidad de caracteres que se solapan entre chunks
            respect_sentences: Si debe respetar límites de oraciones
        """
        self.max_length = max_length
        self.overlap = overlap
        self.respect_sentences = respect_sentences
        
        # Regex para detectar fin de oración
        # Busca: . ! ? seguido de espacio o fin de string
        self.sentence_end_pattern = re.compile(r'([.!?])\s+')
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Divide texto en oraciones
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de oraciones
        """
        # Split en puntos, signos de exclamación e interrogación
        sentences = self.sentence_end_pattern.split(text)
        
        # Recombinar puntuación con oración
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i].strip()
            punct = sentences[i + 1] if i + 1 < len(sentences) else ""
            if sentence:
                result.append(sentence + punct)
        
        # Agregar última oración si existe
        if sentences and sentences[-1].strip():
            result.append(sentences[-1].strip())
        
        return result
    
    def chunk_by_sentences(self, text: str) -> List[str]:
        """
        Divide texto en chunks respetando límites de oraciones
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de chunks
        """
        sentences = self.split_into_sentences(text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Si agregar esta oración excede max_length
            if len(current_chunk) + len(sentence) > self.max_length:
                # Guardar chunk actual si no está vacío
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Si la oración sola es muy larga, dividirla
                if len(sentence) > self.max_length:
                    # Dividir por palabras
                    words = sentence.split()
                    temp_chunk = ""
                    
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 <= self.max_length:
                            temp_chunk += word + " "
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                            temp_chunk = word + " "
                    
                    current_chunk = temp_chunk
                else:
                    current_chunk = sentence + " "
            else:
                current_chunk += sentence + " "
        
        # Agregar último chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def chunk_by_characters(self, text: str) -> List[str]:
        """
        Divide texto en chunks de tamaño fijo con overlap
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.max_length
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self.overlap
        
        return chunks
    
    def chunk(self, text: str) -> List[str]:
        """
        Divide texto en chunks según configuración
        
        Args:
            text: Texto a dividir
            
        Returns:
            Lista de chunks
        """
        if not text or not text.strip():
            return []
        
        if self.respect_sentences:
            return self.chunk_by_sentences(text)
        else:
            return self.chunk_by_characters(text)


def chunk_text(
    text: str,
    max_length: int = 512,
    overlap: int = 50,
    respect_sentences: bool = True,
) -> List[str]:
    """
    Función helper para dividir texto en chunks
    
    Args:
        text: Texto a dividir
        max_length: Longitud máxima por chunk
        overlap: Overlap entre chunks
        respect_sentences: Si respetar límites de oraciones
        
    Returns:
        Lista de chunks
    """
    chunker = TextChunker(
        max_length=max_length,
        overlap=overlap,
        respect_sentences=respect_sentences,
    )
    return chunker.chunk(text)


def chunk_by_tokens(
    text: str,
    max_tokens: int = 512,
    tokenizer=None,
) -> List[str]:
    """
    Divide texto en chunks por cantidad de tokens
    
    Args:
        text: Texto a dividir
        max_tokens: Máximo de tokens por chunk
        tokenizer: Tokenizer a usar (si None, usa aproximación por palabras)
        
    Returns:
        Lista de chunks
    """
    if tokenizer is None:
        # Aproximación: ~1.3 tokens por palabra
        words = text.split()
        max_words = int(max_tokens / 1.3)
        
        chunks = []
        current_chunk = []
        
        for word in words:
            if len(current_chunk) >= max_words:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
            current_chunk.append(word)
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    else:
        # Usar tokenizer real
        tokens = tokenizer.encode(text)
        chunks = []
        
        for i in range(0, len(tokens), max_tokens):
            chunk_tokens = tokens[i:i + max_tokens]
            chunk_text = tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
        
        return chunks


if __name__ == "__main__":
    # Test
    test_text = """
    Este es un texto de prueba. Tiene varias oraciones. Algunas son cortas. 
    Otras son un poco más largas y contienen más información para probar el chunking.
    El objetivo es verificar que el chunker funciona correctamente. ¿Funciona bien?
    ¡Esperemos que sí! Este es el final del texto de prueba.
    """
    
    print("Texto original:")
    print(test_text)
    print("\n" + "=" * 60)
    
    chunker = TextChunker(max_length=100, respect_sentences=True)
    chunks = chunker.chunk(test_text)
    
    print(f"\nChunks generados: {len(chunks)}")
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i} (len={len(chunk)}):")
        print(f"  {chunk}")
