"""
Service for managing ticker mappings using Django ORM.
"""
import re
from typing import Dict, Optional
from .models import TickerMapping


class TickerMappingService:
    """Service for managing ticker mappings using Django ORM."""
    
    @staticmethod
    def get_mappings_file_path():
        """Legacy method - kept for backward compatibility."""
        # This method is no longer used but kept for compatibility
        pass
    
    @staticmethod
    def normalize_company_name(nome: str) -> str:
        """Normalize company name: replace multiple spaces with single space, then strip and upper."""
        return re.sub(r'\s+', ' ', nome.strip()).upper()
    
    @staticmethod
    def load_mappings() -> Dict[str, str]:
        """Load all ticker mappings from database."""
        mappings = TickerMapping.objects.all()
        return {mapping.company_name: mapping.ticker for mapping in mappings}
    
    @staticmethod
    def save_mappings(mappings: Dict[str, str]) -> None:
        """Save ticker mappings to database."""
        for company_name, ticker in mappings.items():
            normalized_name = TickerMappingService.normalize_company_name(company_name)
            TickerMapping.objects.update_or_create(
                company_name=normalized_name,
                defaults={'ticker': ticker.strip().upper()}
            )
    
    @staticmethod
    def get_ticker(nome: str) -> Optional[str]:
        """Get ticker for a company name."""
        nome_normalizado = TickerMappingService.normalize_company_name(nome)
        try:
            mapping = TickerMapping.objects.get(company_name=nome_normalizado)
            return mapping.ticker
        except TickerMapping.DoesNotExist:
            return None
    
    @staticmethod
    def set_ticker(nome: str, ticker: str) -> None:
        """Set ticker mapping for a company name."""
        nome_normalizado = TickerMappingService.normalize_company_name(nome)
        ticker_upper = ticker.strip().upper()
        
        TickerMapping.objects.update_or_create(
            company_name=nome_normalizado,
            defaults={'ticker': ticker_upper}
        )
    
    @staticmethod
    def has_mapping(nome: str) -> bool:
        """Check if a mapping exists for a company name."""
        nome_normalizado = TickerMappingService.normalize_company_name(nome)
        return TickerMapping.objects.filter(company_name=nome_normalizado).exists()
    
    @staticmethod
    def delete_mapping(nome: str) -> bool:
        """Delete a ticker mapping."""
        nome_normalizado = TickerMappingService.normalize_company_name(nome)
        deleted_count = TickerMapping.objects.filter(company_name=nome_normalizado).delete()[0]
        return deleted_count > 0
