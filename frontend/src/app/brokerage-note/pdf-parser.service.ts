import { Injectable } from '@angular/core';
import * as pdfjsLib from 'pdfjs-dist';
import { Operation } from './operation.model';
import { TickerMappingService } from '../portfolio/ticker-mapping/ticker-mapping.service';
import { DebugService } from '../shared/services/debug.service';

@Injectable({
  providedIn: 'root'
})
export class PdfParserService {
  constructor(
    private tickerMappingService: TickerMappingService,
    private debug: DebugService
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
          this.debug.warn(`Erro ao processar página ${pageNum}:`, pageError);
        }
      }

      // Parsear operações do texto extraído
      const operations = await this.parseOperationsFromText(fullText, onTickerRequired);
      
      return operations;
    } catch (error) {
      this.debug.error('Error parsing PDF:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Erro ao processar o PDF: ${errorMessage}. Verifique se o arquivo é uma nota de corretagem válida da B3.`);
    }
  }

  private async parseOperationsFromText(text: string, onTickerRequired?: (nome: string, operationData: any) => Promise<string | null>): Promise<Operation[]> {
    const operations: Operation[] = [];
    const skippedOperations: string[] = [];
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
      // Pattern: 1-BOVESPA   C/V   TIPO_MERCADO   NOME_ACAO   CLASSIFICACAO   @   QTD   PRECO   VALOR   D/C
      // The company name and classification code may be in separate "columns" (separated by 2+ spaces)
      // We need to capture both together: "IGUATEMI S.A UNT N1" or "IOCHP-MAXION ON NM"
      
      // First, try pattern that captures company name and classification as one field
      let bovespaPattern = /1-BOVESPA\s{2,}([CV])\s{2,}([A-Z]+)\s{2,}([A-Z0-9\.\-\s]+?)\s{2,}[#@\s]*\s+(\d+)\s+([\d,\.]+)\s+([\d,\.]+)\s+([DC])/i;
      let bovespaMatch = line.match(bovespaPattern);
      
      let nomeAcaoCompleto = '';
      
      if (bovespaMatch && bovespaMatch.length >= 8) {
        nomeAcaoCompleto = bovespaMatch[3].trim();
        this.debug.log(`📄 Line ${i + 1} matched (pattern 1). Captured: "${nomeAcaoCompleto}"`);
      } else {
        // Try alternative pattern: company name and classification might be separated by 2+ spaces
        // Pattern: 1-BOVESPA   C/V   TIPO   COMPANY_NAME    CLASSIFICATION   @   QTD   PRECO   VALOR   D/C
        bovespaPattern = /1-BOVESPA\s{2,}([CV])\s{2,}([A-Z]+)\s{2,}([A-Z0-9\.\-\s]+?)\s{2,}((?:ON|UNT|PN|PNA|PNAB)\s+(?:NM|N[12]|EJ|ED|EDJ|ATZ))\s+[#@\s]*\s+(\d+)\s+([\d,\.]+)\s+([\d,\.]+)\s+([DC])/i;
        bovespaMatch = line.match(bovespaPattern);
        
        if (bovespaMatch && bovespaMatch.length >= 9) {
          // Group 3 is company name, group 4 is classification
          nomeAcaoCompleto = (bovespaMatch[3].trim() + ' ' + bovespaMatch[4].trim()).trim();
          this.debug.log(`📄 Line ${i + 1} matched (pattern 2). Company: "${bovespaMatch[3].trim()}", Classification: "${bovespaMatch[4].trim()}"`);
          this.debug.log(`📄 Combined: "${nomeAcaoCompleto}"`);
          
          // Adjust match groups for parseBovespaLine (it expects groups 4,5,6,7 for qtd, preco, valor, dc)
          // But now we have groups 5,6,7,8
          bovespaMatch = [
            bovespaMatch[0], // full match
            bovespaMatch[1], // C/V
            bovespaMatch[2], // TIPO_MERCADO
            nomeAcaoCompleto, // combined company + classification
            bovespaMatch[5], // qtd
            bovespaMatch[6], // preco
            bovespaMatch[7], // valor
            bovespaMatch[8]  // D/C
          ];
        }
      }
      
      if (bovespaMatch && nomeAcaoCompleto) {
        // Debug: log what we captured
        this.debug.log(`📄 Full line: "${line}"`);
        
        // If still no classification code, try to find it after the company name
        const classificationPattern = /\b(ON|UNT|PN|PNA|PNAB)\s+(NM|N[12]|EJ|ED|EDJ|ATZ)\b/i;
        if (!classificationPattern.test(nomeAcaoCompleto)) {
          // Try to find classification code in the next part of the line
          const afterField = line.substring(line.indexOf(nomeAcaoCompleto.split(/\s{2,}/)[0]) + nomeAcaoCompleto.split(/\s{2,}/)[0].length);
          const classificationMatch = afterField.match(/\s{2,}((?:ON|UNT|PN|PNA|PNAB)\s+(?:NM|N[12]|EJ|ED|EDJ|ATZ))/i);
          if (classificationMatch) {
            nomeAcaoCompleto = (nomeAcaoCompleto + ' ' + classificationMatch[1]).trim();
            this.debug.log(`📝 Extended field with classification: "${nomeAcaoCompleto}"`);
            // Update the match group
            bovespaMatch[3] = nomeAcaoCompleto;
          }
        }
        
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
        } else {
          skippedOperations.push(`Linha ${i + 1}: "${nomeAcaoCompleto}" - Operação ignorada (ticker não encontrado ou usuário cancelou)`);
          this.debug.warn(`⚠️ Operation skipped for "${nomeAcaoCompleto}" on line ${i + 1}`);
        }
      }
    }

    if (skippedOperations.length > 0) {
      this.debug.warn(`⚠️ ${skippedOperations.length} operation(s) were skipped:`, skippedOperations);
      // Throw error if all operations were skipped
      if (operations.length === 0 && skippedOperations.length > 0) {
        const skippedDetails = skippedOperations.join('\n');
        throw new Error(`Nenhuma operação foi processada. ${skippedOperations.length} operação(ões) foram ignoradas:\n\n${skippedDetails}\n\nVerifique se os tickers estão mapeados corretamente.`);
      }
    }
    
    this.debug.log(`✅ Parsed ${operations.length} operations successfully${skippedOperations.length > 0 ? `, ${skippedOperations.length} skipped` : ''}`);
    
    if (operations.length === 0) {
      throw new Error('Nenhuma operação foi encontrada no PDF. Verifique se o arquivo é uma nota de corretagem válida da B3 e se contém operações no formato esperado.');
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
      this.debug.log(`🔍 Looking up ticker for: "${nomeAcaoCompleto}" -> ${tickerMapeado || 'NOT FOUND'}`);
      
      if (tickerMapeado) {
        titulo = tickerMapeado;
        this.debug.log(`✅ Found ticker in mapping: ${titulo}`);
      } else {
        // 2. Try to extract ticker pattern (4 letters + 1-2 digits) from the complete field
        const codigoMatch = nomeAcaoCompleto.match(/\b([A-Z]{4}\d{1,2})\b/i);
        if (codigoMatch) {
          titulo = codigoMatch[1].toUpperCase();
          this.debug.log(`📝 Extracted ticker from field: ${titulo} (from "${nomeAcaoCompleto}")`);
          // Save mapping using complete field
          this.tickerMappingService.setTicker(nomeAcaoCompleto, titulo);
        } else {
          // 3. Try to DISCOVER ticker via API
          this.debug.log(`🔍 Attempting to discover ticker for: "${nomeAcaoCompleto}"`);
          try {
            const discoveredTicker = await this.tickerMappingService.discoverTicker(nomeAcaoCompleto);
            
            if (discoveredTicker) {
              titulo = discoveredTicker;
              this.debug.log(`✅ Discovered ticker via API: ${titulo}`);
            } else {
              // 4. If not found/discovered, ask user via callback
              this.debug.warn(`⚠️ Ticker not found for "${nomeAcaoCompleto}". ${onTickerRequired ? 'Requesting user input...' : 'No callback provided, skipping operation.'}`);
              
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
                
                this.debug.log(`📞 Calling onTickerRequired for: "${nomeAcaoCompleto}"`);
                const ticker = await onTickerRequired(nomeAcaoCompleto, operationData);
                
                if (ticker) {
                  this.debug.log(`✅ User provided ticker: ${ticker} for "${nomeAcaoCompleto}"`);
                  // Save mapping using complete field
                  this.tickerMappingService.setTicker(nomeAcaoCompleto, ticker);
                  titulo = ticker;
                } else {
                  this.debug.warn(`⚠️ User cancelled ticker input for "${nomeAcaoCompleto}", skipping operation`);
                  return null; // User cancelled - will be added to skippedOperations list
                }
              } else {
                this.debug.error(`❌ No onTickerRequired callback provided, cannot process "${nomeAcaoCompleto}"`);
                return null;
              }
            }
          } catch (err) {
            this.debug.error(`❌ Error during ticker discovery:`, err);
            // Fallback to manual input on error
            if (onTickerRequired) {
               // ... same manual input logic ...
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
                  this.tickerMappingService.setTicker(nomeAcaoCompleto, ticker);
                  titulo = ticker;
                } else {
                   return null;
                }
            } else {
              return null;
            }
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
        this.debug.warn('Dados inválidos na linha:', line);
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
      this.debug.error('Error parsing Bovespa line:', error, 'Line:', line);
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
