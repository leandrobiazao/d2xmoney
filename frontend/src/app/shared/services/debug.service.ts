import { Injectable } from '@angular/core';

/**
 * Centralized logging service with debug mode toggle
 * Enable debug mode by setting localStorage.debugMode = 'true'
 * or by setting environment.debug = true
 */
@Injectable({
  providedIn: 'root'
})
export class DebugService {
  private debugMode: boolean = false;

  constructor() {
    // Check if debug mode is enabled via localStorage
    const debugFlag = localStorage.getItem('debugMode');
    this.debugMode = debugFlag === 'true';
  }

  /**
   * Enable or disable debug mode
   */
  setDebugMode(enabled: boolean): void {
    this.debugMode = enabled;
    localStorage.setItem('debugMode', enabled.toString());
  }

  /**
   * Check if debug mode is enabled
   */
  isDebugEnabled(): boolean {
    return this.debugMode;
  }

  /**
   * Log a debug message (only shown when debug mode is enabled)
   */
  log(...args: any[]): void {
    if (this.debugMode) {
      console.log(...args);
    }
  }

  /**
   * Log a warning message (only shown when debug mode is enabled)
   */
  warn(...args: any[]): void {
    if (this.debugMode) {
      console.warn(...args);
    }
  }

  /**
   * Log an error message (always shown, even in production)
   */
  error(...args: any[]): void {
    console.error(...args);
  }

  /**
   * Log a debug message with a specific label (only shown when debug mode is enabled)
   */
  debug(label: string, ...args: any[]): void {
    if (this.debugMode) {
      console.log(`[${label}]`, ...args);
    }
  }

  /**
   * Group console messages (only shown when debug mode is enabled)
   */
  group(label: string): void {
    if (this.debugMode) {
      console.group(label);
    }
  }

  /**
   * End console group (only shown when debug mode is enabled)
   */
  groupEnd(): void {
    if (this.debugMode) {
      console.groupEnd();
    }
  }
}

