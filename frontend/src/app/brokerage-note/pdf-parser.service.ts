import { Injectable } from '@angular/core';
import * as pdfjsLib from 'pdfjs-dist';
import { Operation } from './operation.model';
import { TickerMappingService } from '../portfolio/ticker-mapping/ticker-mapping.service';

@Injectable({
  providedIn: 'root'
})
export class PdfParserService {
  constructor(
    private tickerMappingService: TickerMappingService
  ) {
    // Configurar worker do PDF.js usando arquivo local
    if (typeof window !== 'undefined') {
      pdfjsLib.GlobalWorkerOptions.workerSrc = '/assets/pdfjs/pdf.worker.min.mjs';
    }
  }

  async parsePdf(file: File, onTickerRequired?: (nome: string, operationData: any) => Promise<string | null>): Promise<Operation[]> {
    try {
      const arrayBuffer = await file.arrayBuffer();
      
      if (!pdfjsLib.GlobalWorkerOptions.workerSrc) {
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/assets/pdfjs/pdf.worker.min.mjs';
      }
      
      const loadingTask = pdfjsLib.getDocument({ 
        data: arrayBuffer,
        verbosity: 0
      });
      
      const pdf = await loadingTask.promise;
      let fullText = '';
      
      // Extrair texto de todas as páginas
      for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
        try {
          const page = await pdf.getPage(pageNum);
          const textContent = await page.getTextContent();
          
          const pageText = textContent.items
            .map((item: any) => {
              if (item.hasEOL) {
                return item.str + '\n';
              }
              return item.str;
            })
            .join(' ');
          fullText += pageText + '\n';
        } catch (pageError) {
          console.warn(`Erro ao processar página ${pageNum}:`, pageError);
        }
      }

      // Parsear operações do texto extraído
      const operations = await this.parseOperationsFromText(fullText, onTickerRequired);
      
      return operations;
    } catch (error) {
      console.error('Error parsing PDF:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Erro ao processar o PDF: ${errorMessage}. Verifique se o arquivo é uma nota de corretagem válida da B3.`);
    }
  }

  private async parseOperationsFromText(text: string, onTickerRequired?: (nome: string, operationData: any) => Promise<string | null>): Promise<Operation[]> {
    const operations: Operation[] = [];
    const normalizedText = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    
    // Extrair data do pregão do PDF
    let pdfDate = '';
    const dateMatch = normalizedText.match(/Data pregão\s+(\d{2}\/\d{2}\/\d{4})/i);
    if (dateMatch) {
      pdfDate = dateMatch[1];
    }
    
    // Extrair número da nota do PDF
    let pdfNota = '';
    const notaMatch = normalizedText.match(/Nr\.\s*nota\s+(\d{9,})/i);
    if (notaMatch) {
      pdfNota = notaMatch[1];
    }
    
    // IMPORTANT: Pattern to capture complete field (company name + classification code as one field)
    // Example: "1-BOVESPA   V   VISTA   3TENTOS ON NM   @   100   14,48   1.448,00   C"
    // The complete field "3TENTOS ON NM" should be treated as a single unified field
    const lines = normalizedText.split('\n');
    
    for (let i = 0; i < lines.length; i++) {
      let line = lines[i].trim();
      
      // Pattern to match B3 format with complete field (company name + classification code)
      // Pattern: 1-BOVESPA   C/V   TIPO_MERCADO   NOME_ACAO_COMPLETO   @   QTD   PRECO   VALOR   D/C
      const bovespaPattern = /1-BOVESPA\s{2,}([CV])\s{2,}([A-Z]+)\s{2,}([A-Z0-9\s]+?)\s{2,}[#@\s]*\s+(\d+)\s+([\d,\.]+)\s+([\d,\.]+)\s+([DC])/i;
      const bovespaMatch = line.match(bovespaPattern);
      
      if (bovespaMatch && bovespaMatch.length >= 8) {
        // Extract nomeAcaoCompleto (complete field including classification code)
        const nomeAcaoCompleto = bovespaMatch[3].trim();
        
        const operation = await this.parseBovespaLine(
          bovespaMatch, 
          line, 
          operations.length + 1, 
          pdfDate, 
          pdfNota, 
          nomeAcaoCompleto, // Pass complete field
          onTickerRequired
        );
        
        if (operation) {
          operations.push(operation);
        }
      }
    }

    return operations;
  }

  private async parseBovespaLine(
    match: RegExpMatchArray, 
    line: string, 
    ordem: number, 
    pdfDate: string = '', 
    pdfNota: string = '',
    nomeAcaoCompleto: string, // Complete field (company name + classification code)
    onTickerRequired?: (nome: string, operationData: any) => Promise<string | null>
  ): Promise<Operation | null> {
    try {
      const tipoOperacao = match[1].toUpperCase() as 'C' | 'V';
      const tipoMercado = match[2].trim();
      
      // Use nomeAcaoCompleto (complete field) for ticker mapping
      // This preserves classification codes (ON NM, ON N2, UNT N1, etc.)
      
      // Extract numeric values
      const quantidade = this.parseNumber(match[4]);
      const preco = this.parseCurrency(match[5]);
      const valorOperacao = this.parseCurrency(match[6]);
      const dc = match[7].toUpperCase() as 'D' | 'C';
      
      // Get ticker using complete field
      let titulo = '';
      
      // 1. Try to get ticker from mapping service using complete field
      const tickerMapeado = this.tickerMappingService.getTicker(nomeAcaoCompleto);
      if (tickerMapeado) {
        titulo = tickerMapeado;
      } else {
        // 2. Try to extract ticker pattern (4 letters + 1-2 digits) from the complete field
        const codigoMatch = nomeAcaoCompleto.match(/\b([A-Z]{4}\d{1,2})\b/i);
        if (codigoMatch) {
          titulo = codigoMatch[1].toUpperCase();
          // Save mapping using complete field
          this.tickerMappingService.setTicker(nomeAcaoCompleto, titulo);
        } else {
          // 3. If not found, ask user via callback
          if (onTickerRequired) {
            const operationData = {
              tipoOperacao,
              tipoMercado,
              quantidade,
              preco,
              valorOperacao,
              dc,
              linha: line
            };
            
            const ticker = await onTickerRequired(nomeAcaoCompleto, operationData);
            if (ticker) {
              // Save mapping using complete field
              this.tickerMappingService.setTicker(nomeAcaoCompleto, ticker);
              titulo = ticker;
            } else {
              return null; // User cancelled
            }
          } else {
            return null;
          }
        }
      }
      
      // Use note number from PDF if available
      let nota = pdfNota || 'N/A';
      if (nota === 'N/A') {
        const notaMatch = line.match(/(\d{9,})/);
        if (notaMatch) {
          nota = notaMatch[1];
        }
      }
      
      // Use date from PDF if available
      let data = pdfDate || new Date().toLocaleDateString('pt-BR');
      if (!pdfDate) {
        const dataMatch = line.match(/(\d{2}\/\d{2}\/\d{4})/);
        if (dataMatch) {
          data = dataMatch[1];
        }
      }
      
      // Validate basic data
      if (!titulo || quantidade === 0 || preco === 0 || valorOperacao === 0) {
        console.warn('Dados inválidos na linha:', line);
        return null;
      }

      // Adjust quantity to negative if sale
      const quantidadeFinal = tipoOperacao === 'V' ? -Math.abs(quantidade) : Math.abs(quantidade);

      return {
        id: this.generateId(),
        tipoOperacao,
        tipoMercado,
        ordem: ordem,
        titulo,
        qtdTotal: quantidade,
        precoMedio: preco,
        quantidade: quantidadeFinal,
        preco,
        valorOperacao: Math.abs(valorOperacao),
        dc,
        notaTipo: 'Bovespa',
        corretora: 'XP',
        nota: nota,
        data,
        clientId: ''
      };
    } catch (error) {
      console.error('Error parsing Bovespa line:', error, 'Line:', line);
      return null;
    }
  }

  private parseNumber(value: string): number {
    if (!value) return 0;
    const cleaned = value.replace(/[^\d,.-]/g, '').replace(/\./g, '').replace(',', '.');
    return parseFloat(cleaned) || 0;
  }

  private parseCurrency(value: string): number {
    if (!value) return 0;
    const cleaned = value.replace(/R\$\s*/gi, '').replace(/[^\d,.-]/g, '').replace(/\./g, '').replace(',', '.');
    return parseFloat(cleaned) || 0;
  }

  private generateId(): string {
    return `op-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

