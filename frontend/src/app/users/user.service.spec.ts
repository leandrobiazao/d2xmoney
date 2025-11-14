import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { UserService } from './user.service';
import { User } from './user.model';

describe('UserService', () => {
  let service: UserService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [UserService]
    });
    service = TestBed.inject(UserService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should get users', () => {
    const mockUsers: User[] = [
      { id: '1', name: 'Test User', cpf: '123.456.789-00', account_provider: 'XP', account_number: '12345-6' }
    ];

    service.getUsers().subscribe(users => {
      expect(users).toEqual(mockUsers);
    });

    const req = httpMock.expectOne('/api/users/');
    expect(req.request.method).toBe('GET');
    req.flush(mockUsers);
  });

  it('should get user by id', () => {
    const mockUser: User = {
      id: '1',
      name: 'Test User',
      cpf: '123.456.789-00',
      account_provider: 'XP',
      account_number: '12345-6'
    };

    service.getUserById('1').subscribe(user => {
      expect(user).toEqual(mockUser);
    });

    const req = httpMock.expectOne('/api/users/1/');
    expect(req.request.method).toBe('GET');
    req.flush(mockUser);
  });

  it('should create user', () => {
    const formData = new FormData();
    formData.append('name', 'New User');
    formData.append('cpf', '123.456.789-00');
    formData.append('account_provider', 'XP');
    formData.append('account_number', '12345-6');

    const mockUser: User = {
      id: '2',
      name: 'New User',
      cpf: '123.456.789-00',
      account_provider: 'XP',
      account_number: '12345-6'
    };

    service.createUser(formData).subscribe(user => {
      expect(user).toEqual(mockUser);
    });

    const req = httpMock.expectOne('/api/users/');
    expect(req.request.method).toBe('POST');
    req.flush(mockUser);
  });

  it('should update user', () => {
    const formData = new FormData();
    formData.append('name', 'Updated User');

    const mockUser: User = {
      id: '1',
      name: 'Updated User',
      cpf: '123.456.789-00',
      account_provider: 'XP',
      account_number: '12345-6'
    };

    service.updateUser('1', formData).subscribe(user => {
      expect(user).toEqual(mockUser);
    });

    const req = httpMock.expectOne('/api/users/1/');
    expect(req.request.method).toBe('PUT');
    req.flush(mockUser);
  });

  it('should delete user', () => {
    service.deleteUser('1').subscribe(() => {
      // Success
    });

    const req = httpMock.expectOne('/api/users/1/');
    expect(req.request.method).toBe('DELETE');
    req.flush(null);
  });
});

