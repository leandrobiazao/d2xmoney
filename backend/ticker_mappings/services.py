"""
Service for managing ticker mappings stored in JSON file.
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
from django.conf import settings


class TickerMappingService:
    """Service for managing ticker mappings in JSON file."""
    
    @staticmethod
    def get_mappings_file_path() -> Path:
        """Get the path to the ticker mappings JSON file."""
        # DATA_DIR is set in settings.py as os.path.join(BASE_DIR, 'data')
        # BASE_DIR is backend/portfolio_api's parent, which is backend/
        # So DATA_DIR should be backend/data
        data_dir = getattr(settings, 'DATA_DIR', None)
        
        if data_dir:
            # Convert string path to Path object
            data_path = Path(data_dir)
        else:
            # Fallback: calculate from current file location
            # services.py is at backend/ticker_mappings/services.py
            # So parent.parent is backend/
            backend_dir = Path(__file__).resolve().parent.parent
            data_path = backend_dir / 'data'
        
        # Ensure directory exists
        data_path.mkdir(parents=True, exist_ok=True)
        
        file_path = data_path / 'ticker.json'
        
        # Debug logging
        print(f"DEBUG: DATA_DIR from settings: {data_dir}")
        print(f"DEBUG: Resolved data_path: {data_path}")
        print(f"DEBUG: Full file path: {file_path}")
        print(f"DEBUG: Data directory exists: {data_path.exists()}")
        
        return file_path
    
    @staticmethod
    def load_mappings() -> Dict[str, str]:
        """Load all ticker mappings from JSON file."""
        file_path = TickerMappingService.get_mappings_file_path()
        
        if not file_path.exists():
            # Return empty dict if file doesn't exist
            return {}
        
        try:
            import re
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Normalize all keys to ensure consistency
                    # Replace multiple spaces with single space, then strip and upper
                    normalized_data = {}
                    needs_save = False
                    for nome, ticker in data.items():
                        nome_normalizado = re.sub(r'\s+', ' ', nome.strip()).upper()
                        if nome != nome_normalizado:
                            needs_save = True
                        normalized_data[nome_normalizado] = ticker
                    
                    # If normalization changed keys, save the normalized version
                    if needs_save:
                        print(f"DEBUG: Normalizing existing mappings file (found {len(normalized_data)} mappings)")
                        TickerMappingService.save_mappings(normalized_data)
                    
                    return normalized_data
                return {}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading ticker mappings: {e}")
            return {}
    
    @staticmethod
    def save_mappings(mappings: Dict[str, str]) -> None:
        """Save ticker mappings to JSON file."""
        file_path = TickerMappingService.get_mappings_file_path()
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Sort mappings by key for consistent output
            sorted_mappings = dict(sorted(mappings.items()))
            
            # Debug: Print file path
            print(f"DEBUG: Saving ticker mappings to: {file_path}")
            print(f"DEBUG: Parent directory exists: {file_path.parent.exists()}")
            print(f"DEBUG: Number of mappings: {len(sorted_mappings)}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sorted_mappings, f, indent=2, ensure_ascii=False)
            
            # Verify file was created
            if file_path.exists():
                print(f"DEBUG: File successfully created at: {file_path}")
            else:
                print(f"DEBUG: ERROR - File was not created!")
                
        except IOError as e:
            print(f"ERROR saving ticker mappings: {e}")
            print(f"ERROR: File path: {file_path}")
            print(f"ERROR: Parent dir exists: {file_path.parent.exists()}")
            raise
        except Exception as e:
            print(f"ERROR: Unexpected error saving ticker mappings: {e}")
            print(f"ERROR: File path: {file_path}")
            raise
    
    @staticmethod
    def get_ticker(nome: str) -> Optional[str]:
        """Get ticker for a company name."""
        mappings = TickerMappingService.load_mappings()
        # Normalize: replace multiple spaces with single space, then strip and upper
        import re
        nome_normalizado = re.sub(r'\s+', ' ', nome.strip()).upper()
        return mappings.get(nome_normalizado)
    
    @staticmethod
    def set_ticker(nome: str, ticker: str) -> None:
        """Set ticker mapping for a company name."""
        mappings = TickerMappingService.load_mappings()
        # Normalize: replace multiple spaces with single space, then strip and upper
        import re
        nome_normalizado = re.sub(r'\s+', ' ', nome.strip()).upper()
        ticker_upper = ticker.strip().upper()
        
        print(f"DEBUG: set_ticker - nome original: '{nome}'")
        print(f"DEBUG: set_ticker - nome normalizado: '{nome_normalizado}'")
        print(f"DEBUG: set_ticker - ticker: '{ticker_upper}'")
        
        mappings[nome_normalizado] = ticker_upper
        TickerMappingService.save_mappings(mappings)
    
    @staticmethod
    def has_mapping(nome: str) -> bool:
        """Check if a mapping exists for a company name."""
        mappings = TickerMappingService.load_mappings()
        nome_normalizado = nome.strip().upper()
        return nome_normalizado in mappings
    
    @staticmethod
    def delete_mapping(nome: str) -> bool:
        """Delete a ticker mapping."""
        mappings = TickerMappingService.load_mappings()
        nome_normalizado = nome.strip().upper()
        
        if nome_normalizado in mappings:
            del mappings[nome_normalizado]
            TickerMappingService.save_mappings(mappings)
            return True
        return False

