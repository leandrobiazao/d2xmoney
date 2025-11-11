export interface User {
  id: string;
  name: string;
  cpf: string;
  account_provider: string;
  account_number: string;
  picture: string | null; // URL or file path, can be null
  created_at?: string; // ISO date, optional
  updated_at?: string; // ISO date, optional
}

