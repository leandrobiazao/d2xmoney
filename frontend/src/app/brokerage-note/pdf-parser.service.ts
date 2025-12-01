import { Injectable } from '@angular/core';
import * as pdfjsLib from 'pdfjs-dist';
import { PDFDocumentProxy } from 'pdfjs-dist';
import { Operation } from './operation.model';
import { FinancialSummary } from './financial-summary.model';
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

  async parsePdf(file: File, onTickerRequired?: (nome: string, operationData: any) => Promise<string | null>): Promise<{ operations: Operation[]; expectedOperationsCount: number | null; financialSummary?: FinancialSummary }> {
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
      
      // Extrair texto de todas as páginas para operações
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

      // Extract last page text separately for financial summary
      const lastPageText = await this.extractLastPageText(pdf);

      // Parsear operações do texto completo de todas as páginas
      const parseResult = await this.parseOperationsFromText(fullText, onTickerRequired);
      const operations = parseResult.operations;
      const expectedOperationsCount = parseResult.expectedOperationsCount;
      
      // Extract financial summary from last page only
      const financialSummary = this.extractFinancialSummary(lastPageText);
      
      return {
        operations,
        expectedOperationsCount,
        financialSummary: financialSummary || undefined
      };
    } catch (error) {
      this.debug.error('Error parsing PDF:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new Error(`Erro ao processar o PDF: ${errorMessage}. Verifique se o arquivo é uma nota de corretagem válida da B3.`);
    }
  }

  private async extractLastPageText(pdf: PDFDocumentProxy): Promise<string> {
    try {
      const totalPages = pdf.numPages;
      if (totalPages === 0) {
        return '';
      }
      
      const lastPage = await pdf.getPage(totalPages);
      const textContent = await lastPage.getTextContent();
      
      const lastPageText = textContent.items
        .map((item: any) => {
          if (item.hasEOL) {
            return item.str + '\n';
          }
          return item.str;
        })
        .join(' ');
      
      this.debug.log(`✅ Extracted text from last page (page ${totalPages})`);
      return lastPageText;
    } catch (error) {
      this.debug.error('Error extracting last page text:', error);
      return '';
    }
  }

  private extractFinancialSummary(lastPageText: string): FinancialSummary | null {
    if (!lastPageText || lastPageText.trim().length === 0) {
      this.debug.warn('⚠️ Last page text is empty, cannot extract financial summary');
      return null;
    }

    const summary: FinancialSummary = {};
    const normalizedText = lastPageText.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    try {
      // Helper function to parse Brazilian number format
      const parseBrazilianNumber = (value: string): number | undefined => {
        if (!value) return undefined;
        // Remove spaces, handle C/D indicators, and parse Brazilian format (comma as decimal)
        const cleaned = value.replace(/[^\d,.-CD]/g, '').trim();
        if (!cleaned || cleaned === 'C' || cleaned === 'D') return undefined;
        
        // Remove C/D indicator if present
        const withoutCD = cleaned.replace(/[CD]$/i, '').trim();
        if (!withoutCD) return undefined;
        
        // Replace comma with dot for decimal, remove dots for thousands
        const normalized = withoutCD.replace(/\./g, '').replace(',', '.');
        const parsed = parseFloat(normalized);
        return isNaN(parsed) ? undefined : parsed;
      };

      // Helper function to extract value after label
      const extractValue = (label: string, text: string): number | undefined => {
        const patterns = [
          new RegExp(`${label}[:\\s]+([\\d.,\\s]+[CD]?)\\b`, 'i'),
          new RegExp(`${label}\\s+([\\d.,\\s]+[CD]?)\\b`, 'i'),
          new RegExp(`${label}\\s*:\\s*([\\d.,\\s]+[CD]?)\\b`, 'i'),
        ];

        for (const pattern of patterns) {
          const match = text.match(pattern);
          if (match && match[1]) {
            return parseBrazilianNumber(match[1]);
          }
        }
        return undefined;
      };

      // Resumo dos Negócios
      summary.debentures = extractValue('Debêntures', normalizedText);
      summary.vendas_a_vista = extractValue('Vendas à vista', normalizedText) || 
                              extractValue('Vendas a vista', normalizedText);
      summary.compras_a_vista = extractValue('Compras à vista', normalizedText) || 
                                extractValue('Compras a vista', normalizedText);
      summary.valor_das_operacoes = extractValue('Valor das operações', normalizedText);

      // Resumo Financeiro
      summary.clearing = extractValue('Clearing', normalizedText);
      summary.valor_liquido_operacoes = extractValue('Valor líquido das operações', normalizedText) ||
                                        extractValue('Valor liquido das operacoes', normalizedText);
      summary.taxa_liquidacao = extractValue('Taxa de liquidação', normalizedText) ||
                                extractValue('Taxa de liquidacao', normalizedText);
      summary.taxa_registro = extractValue('Taxa de registro', normalizedText);
      summary.total_cblc = extractValue('Total CBLC', normalizedText);
      summary.bolsa = extractValue('Bolsa', normalizedText);
      summary.emolumentos = extractValue('Emolumentos', normalizedText);
      summary.taxa_transferencia_ativos = extractValue('Taxa de transferência de ativos', normalizedText) ||
                                          extractValue('Taxa de transferencia de ativos', normalizedText);
      summary.total_bovespa = extractValue('Total Bovespa', normalizedText);

      // Custos Operacionais
      summary.taxa_operacional = extractValue('Taxa operacional', normalizedText);
      summary.execucao = extractValue('Execução', normalizedText) ||
                        extractValue('Execucao', normalizedText);
      summary.taxa_custodia = extractValue('Taxa de custódia', normalizedText) ||
                              extractValue('Taxa de custodia', normalizedText);
      summary.impostos = extractValue('Impostos', normalizedText);
      summary.irrf_operacoes = extractValue('I.R.R.F. s/ operações', normalizedText) ||
                               extractValue('IRRF s/ operacoes', normalizedText) ||
                               extractValue('IRRF s/ operações', normalizedText);
      summary.irrf_base = extractValue('I.R.R.F. s/ base', normalizedText) ||
                         extractValue('IRRF s/ base', normalizedText);
      summary.outros_custos = extractValue('Outros', normalizedText);
      summary.total_custos_despesas = extractValue('Total de custos', normalizedText) ||
                                      extractValue('Total de custos e despesas', normalizedText);
      summary.liquido = extractValue('Líquido para', normalizedText) ||
                       extractValue('Liquido para', normalizedText);

      // Extract date from "Líquido para DD/MM/YYYY"
      const liquidoDateMatch = normalizedText.match(/Líquido para\s+(\d{2}\/\d{2}\/\d{4})/i) ||
                               normalizedText.match(/Liquido para\s+(\d{2}\/\d{2}\/\d{4})/i);
      if (liquidoDateMatch && liquidoDateMatch[1]) {
        summary.liquido_data = liquidoDateMatch[1];
      }

      // Check if we found any values
      const hasAnyValue = Object.values(summary).some(value => value !== undefined);
      
      if (hasAnyValue) {
        this.debug.log('✅ Extracted financial summary from last page:', summary);
        return summary;
      } else {
        this.debug.warn('⚠️ No financial summary values found on last page');
        return null;
      }
    } catch (error) {
      this.debug.error('Error extracting financial summary:', error);
      return null;
    }
  }

  private async parseOperationsFromText(text: string, onTickerRequired?: (nome: string, operationData: any) => Promise<string | null>): Promise<{ operations: Operation[]; expectedOperationsCount: number | null }> {
    const operations: Operation[] = [];
    const skippedOperations: string[] = [];
    const normalizedText = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    
    // Extrair data do pregão do PDF
    let pdfDate = '';
    const dateMatch = normalizedText.match(/Data pregão\s+(\d{2}\/\d{2}\/\d{4})/i);
    if (dateMatch) {
      pdfDate = dateMatch[1];
    }
    
    // Count expected operations by counting lines that match the B3 operation pattern
    // This gives us the total number of operation lines in the PDF
    const allLines = normalizedText.split('\n');
    let expectedOperationsCount: number | null = null;
    
    // Count lines that match the B3 operation pattern (1-BOVESPA)
    const bovespaLinePattern = /1-BOVESPA\s{2,}[CV]\s{2,}[A-Z]+\s{2,}/i;
    const matchingLines = allLines.filter(line => bovespaLinePattern.test(line.trim()));
    if (matchingLines.length > 0) {
      expectedOperationsCount = matchingLines.length;
      this.debug.log(`📊 Found ${expectedOperationsCount} operation line(s) in PDF (by pattern matching)`);
    } else {
      this.debug.warn('⚠️ Could not determine expected operations count from PDF');
    }
    
    // Extrair número da nota do PDF
    // Try multiple patterns to find note number
    let pdfNota = '';
    
    // Pattern 1: "Nr. nota" or "Nr nota" or "Nr.nota" followed by number
    let notaMatch = normalizedText.match(/Nr\.?\s*nota\s*:?\s*(\d{8,})/i);
    if (notaMatch) {
      pdfNota = notaMatch[1];
      this.debug.log(`✅ Found note number (pattern 1): ${pdfNota}`);
    } else {
      // Pattern 2: Look for "nota" followed by a number (8+ digits)
      notaMatch = normalizedText.match(/nota\s*:?\s*(\d{8,})/i);
      if (notaMatch) {
        pdfNota = notaMatch[1];
        this.debug.log(`✅ Found note number (pattern 2): ${pdfNota}`);
      } else {
        // Pattern 3: Look for standalone 8-9 digit numbers that could be note numbers
        // Usually note numbers are 8-9 digits and appear near the top of the document
        const headerLines = normalizedText.split('\n').slice(0, 20); // Check first 20 lines
        for (const line of headerLines) {
          const numberMatch = line.match(/(\d{8,9})/);
          if (numberMatch) {
            // Check if it's not a date (DD/MM/YYYY or similar)
            const datePattern = /\d{2}\/\d{2}\/\d{4}/;
            if (!datePattern.test(line)) {
              pdfNota = numberMatch[1];
              this.debug.log(`✅ Found note number (pattern 3): ${pdfNota} in line: ${line.substring(0, 50)}`);
              break;
            }
          }
        }
      }
    }
    
    if (!pdfNota) {
      this.debug.warn('⚠️ Could not extract note number from PDF header');
    }
    
    // IMPORTANT: Pattern to capture complete field (company name + classification code as one field)
    // Example: "1-BOVESPA   V   VISTA   3TENTOS ON NM   @   100   14,48   1.448,00   C"
    // The complete field "3TENTOS ON NM" should be treated as a single unified field
    const lines = allLines;
    
    for (let i = 0; i < lines.length; i++) {
      let line = lines[i].trim();
      
      // Pattern to match B3 format with complete field (company name + classification code)
      // Pattern: 1-BOVESPA   C/V   TIPO_MERCADO   NOME_ACAO   CLASSIFICACAO   @   QTD   PRECO   VALOR   D/C
      // The company name and classification code may be in separate "columns" (separated by 2+ spaces)
      // We need to capture both together: "IGUATEMI S.A UNT N1" or "IOCHP-MAXION ON NM"
      
      // First, try pattern that captures company name and classification as one field
      // More flexible pattern: capture everything between market type and quantity
      // 1-BOVESPA [C/V] [MARKET] [NAME.....] [#] [QTD] [PRICE] [VALUE] [D/C]
      let bovespaPattern = /1-BOVESPA\s{2,}([CV])\s{2,}([A-Z]+)\s{2,}(.+?)\s{2,}[#@]?\d*\s+(\d+)\s+([\d,\.]+)\s+([\d,\.]+)\s+([DC])/i;
      let bovespaMatch = line.match(bovespaPattern);
      
      let nomeAcaoCompleto = '';
      
      if (bovespaMatch && bovespaMatch.length >= 8) {
        nomeAcaoCompleto = bovespaMatch[3].trim();
        // Clean up trailing special chars often found before quantity
        nomeAcaoCompleto = nomeAcaoCompleto.replace(/\s+[#@]\s*$/, '').trim();
        
        this.debug.log(`📄 Line ${i + 1} matched (flexible pattern). Captured: "${nomeAcaoCompleto}"`);
      } else {
        // Fallback to stricter pattern if flexible fails (unlikely but safe)
        // Pattern: 1-BOVESPA   C/V   TIPO   COMPANY_NAME    CLASSIFICATION   @   QTD   PRECO   VALOR   D/C
        bovespaPattern = /1-BOVESPA\s{2,}([CV])\s{2,}([A-Z]+)\s{2,}([A-Z0-9\.\-\s]+?)\s{2,}((?:ON|UNT|PN|PNA|PNAB)\s+(?:NM|N[12]|EJ|ED|EDJ|ATZ))\s+[#@\s]*\s+(\d+)\s+([\d,\.]+)\s+([\d,\.]+)\s+([DC])/i;
        bovespaMatch = line.match(bovespaPattern);
        
        if (bovespaMatch && bovespaMatch.length >= 9) {
          // Group 3 is company name, group 4 is classification
          nomeAcaoCompleto = (bovespaMatch[3].trim() + ' ' + bovespaMatch[4].trim()).trim();
          this.debug.log(`📄 Line ${i + 1} matched (strict pattern). Combined: "${nomeAcaoCompleto}"`);
          
          // Adjust match groups for parseBovespaLine
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
        
        // Process operation - this will wait for user input if ticker is not found
        this.debug.log(`🔄 Processing operation ${operations.length + 1} of expected ${expectedOperationsCount || 'unknown'}: "${nomeAcaoCompleto}"`);
        this.debug.log(`🔄 Line content: "${line.substring(0, 100)}..."`);
        
        try {
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
            this.debug.log(`✅ Operation ${operations.length} processed successfully: ${operation.titulo}`);
          } else {
            const skipMsg = `Linha ${i + 1}: "${nomeAcaoCompleto}" - Operação ignorada (ticker não encontrado ou usuário cancelou)`;
            skippedOperations.push(skipMsg);
            this.debug.warn(`⚠️ Operation skipped for "${nomeAcaoCompleto}" on line ${i + 1} - operation returned null`);
            this.debug.warn(`⚠️ Skip reason: parseBovespaLine returned null - this should NOT happen if onTickerRequired is working`);
            
            // If we have an expected count and we're skipping, this is a problem
            if (expectedOperationsCount !== null) {
              this.debug.error(`❌ Skipping operation when we expect ${expectedOperationsCount} total. Current: ${operations.length}, Skipped: ${skippedOperations.length}`);
              this.debug.error(`❌ This operation will cause validation to fail!`);
            }
          }
        } catch (error) {
          const errorMsg = `Linha ${i + 1}: "${nomeAcaoCompleto}" - Erro ao processar: ${error instanceof Error ? error.message : 'Erro desconhecido'}`;
          skippedOperations.push(errorMsg);
          this.debug.error(`❌ Error processing operation on line ${i + 1}:`, error);
          
          // If we have an expected count and we're skipping, this is a problem
          if (expectedOperationsCount !== null) {
            this.debug.error(`❌ Error processing operation when we expect ${expectedOperationsCount} total. Current: ${operations.length}, Skipped: ${skippedOperations.length}`);
          }
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
    
    // Validate operations count if we have an expected count
    if (expectedOperationsCount !== null && operations.length !== expectedOperationsCount) {
      const skippedCount = skippedOperations.length;
      const totalExpected = expectedOperationsCount;
      const totalParsed = operations.length;
      const discrepancy = totalExpected - totalParsed;
      
      this.debug.error(`❌ Operations count mismatch! Expected: ${totalExpected}, Parsed: ${totalParsed}, Skipped: ${skippedCount}`);
      
      throw new Error(
        `Validação falhou: O PDF contém ${totalExpected} operação(ões), mas apenas ${totalParsed} foram processadas com sucesso. ` +
        `${skippedCount > 0 ? `${skippedCount} operação(ões) foram ignoradas (ticker não encontrado ou usuário cancelou). ` : ''}` +
        `Por favor, verifique os tickers e tente novamente. Operações não serão salvas.`
      );
    }
    
    return { operations, expectedOperationsCount };
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
      
      // Debug: Log all available mappings for troubleshooting
      const allMappings = this.tickerMappingService.getAllMappings();
      const hashRelatedMappings = Object.entries(allMappings)
        .filter(([nome]) => nome.toUpperCase().includes('HASH') || nome.toUpperCase().includes('BARI'))
        .map(([nome, ticker]) => `${nome} -> ${ticker}`);
      if (hashRelatedMappings.length > 0) {
        this.debug.log(`🔍 Available HASH/BARI mappings:`, hashRelatedMappings);
      }
      
      // Normalize name for lookup (same logic as TickerMappingService)
      const normalizedNome = nomeAcaoCompleto.replace(/\s+/g, ' ').trim().toUpperCase();
      this.debug.log(`🔍 Normalized name for lookup: "${normalizedNome}"`);
      
      // IMPORTANT: Always check mapping FIRST
      // This ensures that once a user provides a ticker, it's reused for subsequent occurrences
      // 1. Try to get ticker from mapping service using complete field
      let tickerMapeado = this.tickerMappingService.getTicker(nomeAcaoCompleto);
      this.debug.log(`🔍 Looking up ticker for: "${nomeAcaoCompleto}" -> ${tickerMapeado || 'NOT FOUND'}`);
      
      // 1b. If not found, try variations of the name (without classification codes, without trailing "CI", etc.)
      if (!tickerMapeado) {
        // Try without classification codes (ON NM, UNT N1, etc.)
        const nomeSemClassificacao = nomeAcaoCompleto.replace(/\s+(ON|UNT|PN|PNA|PNAB)\s+(NM|N[12]|EJ|ED|EDJ|ATZ)\s*$/i, '').trim();
        if (nomeSemClassificacao !== nomeAcaoCompleto) {
          tickerMapeado = this.tickerMappingService.getTicker(nomeSemClassificacao);
          this.debug.log(`🔍 Trying without classification: "${nomeSemClassificacao}" -> ${tickerMapeado || 'NOT FOUND'}`);
        }
        
        // Try removing trailing "CI" (common in ETF names)
        if (!tickerMapeado) {
          const nomeSemCI = nomeAcaoCompleto.replace(/\s+CI\s*$/i, '').trim();
          if (nomeSemCI !== nomeAcaoCompleto) {
            tickerMapeado = this.tickerMappingService.getTicker(nomeSemCI);
            this.debug.log(`🔍 Trying without trailing CI: "${nomeSemCI}" -> ${tickerMapeado || 'NOT FOUND'}`);
          }
        }
        
        // Try both: without classification AND without CI
        if (!tickerMapeado) {
          const nomeSemClassESemCI = nomeSemClassificacao.replace(/\s+CI\s*$/i, '').trim();
          if (nomeSemClassESemCI !== nomeAcaoCompleto && nomeSemClassESemCI !== nomeSemClassificacao) {
            tickerMapeado = this.tickerMappingService.getTicker(nomeSemClassESemCI);
            this.debug.log(`🔍 Trying without classification and CI: "${nomeSemClassESemCI}" -> ${tickerMapeado || 'NOT FOUND'}`);
          }
        }
      }
      
      if (tickerMapeado) {
        titulo = tickerMapeado;
        this.debug.log(`✅ Found ticker in mapping: ${titulo}`);
      }
      
      if (!titulo) {
        // 2. Try to extract ticker pattern (4 letters + 1-2 digits) from the complete field
        const codigoMatch = nomeAcaoCompleto.match(/\b([A-Z]{4}\d{1,2})\b/i);
        if (codigoMatch) {
          const extractedTicker = codigoMatch[1].toUpperCase();
          const matchIndex = codigoMatch.index!;
          
          // Check if the ticker is a standalone word (has space before and after, or at start/end)
          const beforeChar = matchIndex > 0 ? nomeAcaoCompleto[matchIndex - 1] : ' ';
          const afterChar = matchIndex + extractedTicker.length < nomeAcaoCompleto.length 
            ? nomeAcaoCompleto[matchIndex + extractedTicker.length] 
            : ' ';
          
          // Only auto-extract if ticker is clearly a standalone word (not part of longer word)
          const isStandaloneTicker = (beforeChar === ' ' || matchIndex === 0) && 
                                     (afterChar === ' ' || afterChar === undefined || /[^A-Z0-9]/.test(afterChar));
          
          if (isStandaloneTicker) {
            titulo = extractedTicker;
            this.debug.log(`📝 Extracted ticker from field: ${titulo} (from "${nomeAcaoCompleto}")`);
            // Save mapping using complete field
            this.tickerMappingService.setTicker(nomeAcaoCompleto, titulo);
          } else {
            // Ticker pattern found but not standalone - ask user
            this.debug.warn(`⚠️ Ticker pattern "${extractedTicker}" found in "${nomeAcaoCompleto}" but is not standalone. Requesting user input...`);
          }
        }
      }
      
      if (!titulo) {
        // 3. If not found in mapping and no ticker pattern, ask user via callback
        this.debug.warn(`⚠️ Ticker not found for "${nomeAcaoCompleto}". Requesting user input...`);
          this.debug.log(`📋 All attempted variations:`, {
            original: nomeAcaoCompleto,
            withoutClassification: nomeAcaoCompleto.replace(/\s+(ON|UNT|PN|PNA|PNAB)\s+(NM|N[12]|EJ|ED|EDJ|ATZ)\s*$/i, '').trim(),
            withoutCI: nomeAcaoCompleto.replace(/\s+CI\s*$/i, '').trim()
          });
          
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
            this.debug.log(`📞 Operation data:`, operationData);
            this.debug.log(`📞 onTickerRequired function exists: ${!!onTickerRequired}`);
            
            try {
              const ticker = await onTickerRequired(nomeAcaoCompleto, operationData);
              
              this.debug.log(`📞 onTickerRequired returned: ${ticker || 'null'}`);
              
              if (ticker && ticker.trim().length > 0) {
                const tickerUpper = ticker.trim().toUpperCase();
                this.debug.log(`✅ User provided ticker: ${tickerUpper} for "${nomeAcaoCompleto}"`);
                
                // Save mapping using complete field AND variations
                // IMPORTANT: Save the original name exactly as extracted from PDF
                this.debug.log(`💾 Saving mapping for original name: "${nomeAcaoCompleto}" -> ${tickerUpper}`);
                this.tickerMappingService.setTicker(nomeAcaoCompleto, tickerUpper);
                
                // Also save variations for future use
                const nomeSemClassificacao = nomeAcaoCompleto.replace(/\s+(ON|UNT|PN|PNA|PNAB)\s+(NM|N[12]|EJ|ED|EDJ|ATZ)\s*$/i, '').trim();
                if (nomeSemClassificacao !== nomeAcaoCompleto) {
                  this.debug.log(`💾 Saving mapping for variation (without classification): "${nomeSemClassificacao}" -> ${tickerUpper}`);
                  this.tickerMappingService.setTicker(nomeSemClassificacao, tickerUpper);
                }
                
                // For names with CI, also save without CI
                const nomeSemCI = nomeAcaoCompleto.replace(/\s+CI\s*$/i, '').trim();
                if (nomeSemCI !== nomeAcaoCompleto && nomeSemCI !== nomeSemClassificacao) {
                  this.debug.log(`💾 Saving mapping for variation (without CI): "${nomeSemCI}" -> ${tickerUpper}`);
                  this.tickerMappingService.setTicker(nomeSemCI, tickerUpper);
                }
                
                // Verify the mapping was saved locally
                const savedTicker = this.tickerMappingService.getTicker(nomeAcaoCompleto);
                if (savedTicker === tickerUpper) {
                  this.debug.log(`✅ Verified: Mapping saved successfully in local cache`);
                } else {
                  this.debug.warn(`⚠️ Warning: Mapping not found in local cache after save. Expected: ${tickerUpper}, Got: ${savedTicker}`);
                }
                
                titulo = tickerUpper;
              } else {
                this.debug.warn(`⚠️ User cancelled or provided empty ticker for "${nomeAcaoCompleto}", skipping operation`);
                return null; // User cancelled - will be added to skippedOperations list
              }
            } catch (error) {
              this.debug.error(`❌ Error in onTickerRequired callback:`, error);
              return null;
            }
          } else {
            this.debug.error(`❌ No onTickerRequired callback provided, cannot process "${nomeAcaoCompleto}"`);
            return null;
          }
        }
      
      let nota = pdfNota || '';
      // Try to find note number in the line if not found in header
      if (!nota) {
        const notaMatch = line.match(/(\d{9,})/);
        if (notaMatch) {
          nota = notaMatch[1];
        }
      }
      // Use empty string instead of 'N/A' when not found
      
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
