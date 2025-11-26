import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { FIIProfile } from './fiis.models';

@Injectable({
    providedIn: 'root'
})
export class FIIService {
    private apiUrl = 'http://localhost:8000/api/fiis';

    constructor(private http: HttpClient) { }

    getFIIProfiles(): Observable<FIIProfile[]> {
        return this.http.get<FIIProfile[]>(`${this.apiUrl}/profiles/`);
    }

    getFIIProfile(ticker: string): Observable<FIIProfile> {
        return this.http.get<FIIProfile>(`${this.apiUrl}/profiles/${ticker}/`);
    }
}
