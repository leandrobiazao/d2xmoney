import { Operation } from '../brokerage-note/operation.model';
import { Position } from './position.model';

export interface Portfolio {
  clientId: string;
  operations: Operation[];
  positions: Position[];
  lastUpdated: string; // ISO timestamp
}

