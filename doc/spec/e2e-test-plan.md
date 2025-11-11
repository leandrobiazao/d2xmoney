# E2E Test Plan - D2X Money Manager

## Test Environment
- **Application**: D2X Money Manager
- **Frontend URL**: http://localhost:4400
- **Backend URL**: http://localhost:8000
- **Test Framework**: Playwright MCP Server
- **Browser**: Chromium

## Test Scenarios

### TC-001: Application Load and Title Verification
**Objective**: Verify application loads with correct title

**Steps**:
1. Navigate to http://localhost:4400
2. Verify page title is "D2X Money Manager"
3. Verify header displays "Portfolio Management System"
4. Verify navigation links are visible (Portfolio, Histórico)

**Expected Results**:
- ✅ Page title: "D2X Money Manager"
- ✅ Header shows correct branding
- ✅ Navigation links functional

---

### TC-002: User Management - Create User (Without Picture)
**Objective**: Verify user can be created without a picture

**Steps**:
1. Click "Criar Novo Usuário" button
2. Fill in form:
   - Nome: "Test User"
   - CPF: "123.456.789-00" (valid CPF)
   - Corretora: "XP Investimentos"
   - Número da Conta: "12345-6"
   - Foto: Leave empty (optional)
3. Click "Criar Usuário"
4. Verify user is created successfully
5. Verify user appears in user list

**Expected Results**:
- ✅ Form accepts submission without picture
- ✅ User created successfully
- ✅ User appears in list
- ✅ No picture error displayed

---

### TC-003: User Management - Create User (With Picture)
**Objective**: Verify user can be created with a picture

**Steps**:
1. Click "Criar Novo Usuário" button
2. Fill in form with all fields including picture
3. Upload a valid image file (JPEG/PNG, < 5MB)
4. Verify picture preview appears
5. Submit form
6. Verify user created with picture

**Expected Results**:
- ✅ Picture preview displayed
- ✅ User created with picture
- ✅ Picture displayed in user list

---

### TC-004: CPF Validation
**Objective**: Verify CPF validation works correctly

**Steps**:
1. Open create user form
2. Enter invalid CPF: "123.456.789-01"
3. Verify error message appears
4. Enter valid CPF: "123.456.789-00"
5. Verify no error message
6. Verify CPF is auto-formatted

**Expected Results**:
- ✅ Invalid CPF shows error
- ✅ Valid CPF accepted
- ✅ CPF auto-formatted as XXX.XXX.XXX-XX

---

### TC-005: User Selection and Portfolio Display
**Objective**: Verify selecting a user displays their portfolio

**Steps**:
1. Create a user (or use existing)
2. Click on user in user list
3. Verify user is selected (highlighted)
4. Verify portfolio component appears
5. Verify "Selecione um cliente..." message disappears

**Expected Results**:
- ✅ User selected state visible
- ✅ Portfolio component displayed
- ✅ User name shown in portfolio header

---

### TC-006: Brokerage Note Upload
**Objective**: Verify PDF upload and processing

**Steps**:
1. Select a user
2. Click "Selecionar arquivo PDF" in upload section
3. Select a valid B3 brokerage note PDF
4. Click "Upload e Processar PDF"
5. Verify processing status
6. Verify operations are extracted
7. Verify success message displayed

**Expected Results**:
- ✅ PDF file selected
- ✅ Processing indicator shown
- ✅ Operations extracted successfully
- ✅ Success message with operation count

---

### TC-007: Ticker Mapping Dialog
**Objective**: Verify ticker mapping dialog appears for unknown tickers

**Steps**:
1. Upload PDF with unknown company name
2. Verify ticker dialog appears
3. Enter valid ticker (e.g., "PETR4")
4. Click "Confirmar"
5. Verify processing continues
6. Verify ticker is saved

**Expected Results**:
- ✅ Dialog appears with company name
- ✅ Ticker input accepts valid format
- ✅ Processing continues after confirmation
- ✅ Ticker mapping saved

---

### TC-008: Portfolio Positions Calculation
**Objective**: Verify positions are calculated correctly from operations

**Steps**:
1. Upload PDF with buy operations
2. Verify positions appear in "Posições Atuais" section
3. Verify correct quantities and prices
4. Upload another PDF with sell operations
5. Verify positions update correctly

**Expected Results**:
- ✅ Positions calculated correctly
- ✅ Weighted average price correct
- ✅ Quantities updated after sells
- ✅ Positions removed when quantity reaches zero

---

### TC-009: Portfolio Operations Filtering
**Objective**: Verify operation filters work correctly

**Steps**:
1. Select user with operations
2. Apply filter by Título (e.g., "ANIM3")
3. Verify only matching operations shown
4. Apply filter by Tipo Operação (Compra/Venda)
5. Verify filtered results
6. Apply date range filter
7. Verify date filtering works
8. Click "Limpar Filtros"
9. Verify all operations shown again

**Expected Results**:
- ✅ Título filter works
- ✅ Tipo Operação filter works
- ✅ Date range filter works
- ✅ Clear filters resets all

---

### TC-010: Delete Operation
**Objective**: Verify operations can be deleted

**Steps**:
1. Select user with operations
2. Click delete button (×) on an operation
3. Confirm deletion
4. Verify operation removed
5. Verify positions recalculated

**Expected Results**:
- ✅ Confirmation dialog appears
- ✅ Operation deleted
- ✅ Positions recalculated
- ✅ Portfolio updated

---

### TC-011: Brokerage History Navigation
**Objective**: Verify navigation to brokerage history

**Steps**:
1. Click "Histórico" link in header
2. Verify history list page loads
3. Verify URL is /brokerage-history
4. Verify history list component displayed

**Expected Results**:
- ✅ Navigation works
- ✅ History page loads
- ✅ URL updated correctly

---

### TC-012: Brokerage History List
**Objective**: Verify history list displays processed notes

**Steps**:
1. Navigate to /brokerage-history
2. Verify history list loads
3. Verify filters are available
4. Apply filters (user, date, note number)
5. Verify filtered results

**Expected Results**:
- ✅ History list displayed
- ✅ Filters functional
- ✅ Filtered results correct

---

### TC-013: Brokerage History Detail
**Objective**: Verify note detail view

**Steps**:
1. Navigate to history list
2. Click "Ver" on a note
3. Verify detail page loads
4. Verify note metadata displayed
5. Verify operations table displayed
6. Click "Voltar"
7. Verify return to list

**Expected Results**:
- ✅ Detail page loads
- ✅ All metadata shown
- ✅ Operations displayed correctly
- ✅ Back navigation works

---

### TC-014: Delete Note from History
**Objective**: Verify notes can be deleted from history

**Steps**:
1. Navigate to history detail
2. Click "Excluir Nota"
3. Confirm deletion
4. Verify note removed
5. Verify return to list

**Expected Results**:
- ✅ Confirmation dialog
- ✅ Note deleted
- ✅ Returned to list
- ✅ Note no longer in list

---

### TC-015: Form Validation
**Objective**: Verify all form validations work

**Steps**:
1. Open create user form
2. Try to submit empty form
3. Verify all required field errors
4. Enter invalid data in each field
5. Verify specific error messages
6. Enter valid data
7. Verify no errors

**Expected Results**:
- ✅ Required field validation
- ✅ CPF format validation
- ✅ CPF checksum validation
- ✅ Account number format validation
- ✅ Picture optional (no error if empty)

---

### TC-016: Error Handling
**Objective**: Verify error handling and messages

**Steps**:
1. Test with backend offline
2. Verify error messages displayed
3. Test with invalid PDF
4. Verify appropriate error message
5. Test with network errors
6. Verify user-friendly error messages

**Expected Results**:
- ✅ Error messages displayed
- ✅ Messages are user-friendly
- ✅ Application doesn't crash
- ✅ User can retry operations

---

### TC-017: Responsive Design
**Objective**: Verify application works on different screen sizes

**Steps**:
1. Test on desktop (1920x1080)
2. Test on tablet (768x1024)
3. Test on mobile (375x667)
4. Verify all components visible
5. Verify navigation works
6. Verify forms usable

**Expected Results**:
- ✅ Layout adapts to screen size
- ✅ All features accessible
- ✅ No horizontal scrolling issues
- ✅ Touch targets appropriate size

---

### TC-018: Currency Formatting
**Objective**: Verify currency values formatted as BRL

**Steps**:
1. View portfolio with operations
2. Verify all currency values formatted as R$ X.XXX,XX
3. Verify positions show correct formatting
4. Verify operation values formatted

**Expected Results**:
- ✅ All currencies formatted as BRL
- ✅ Decimal separator: comma
- ✅ Thousands separator: period
- ✅ Currency symbol: R$

---

### TC-019: Empty States
**Objective**: Verify empty states display correctly

**Steps**:
1. View user list with no users
2. Verify empty state message
3. View portfolio with no operations
4. Verify appropriate empty state
5. View history with no notes
6. Verify empty state message

**Expected Results**:
- ✅ Empty states displayed
- ✅ Messages are helpful
- ✅ Actions available (e.g., "Create User" button)

---

### TC-020: Integration Flow - Complete Workflow
**Objective**: Test complete user workflow

**Steps**:
1. Create a new user (without picture)
2. Select the user
3. Upload a brokerage note PDF
4. Handle any ticker mapping dialogs
5. Verify operations added to portfolio
6. Verify positions calculated
7. Filter operations
8. Delete an operation
9. Verify positions updated
10. Navigate to history
11. Verify note in history
12. View note detail
13. Return to portfolio

**Expected Results**:
- ✅ Complete workflow functional
- ✅ Data persists correctly
- ✅ All features work together
- ✅ No errors in console

---

## Test Execution Checklist

- [ ] TC-001: Application Load and Title Verification
- [ ] TC-002: User Management - Create User (Without Picture)
- [ ] TC-003: User Management - Create User (With Picture)
- [ ] TC-004: CPF Validation
- [ ] TC-005: User Selection and Portfolio Display
- [ ] TC-006: Brokerage Note Upload
- [ ] TC-007: Ticker Mapping Dialog
- [ ] TC-008: Portfolio Positions Calculation
- [ ] TC-009: Portfolio Operations Filtering
- [ ] TC-010: Delete Operation
- [ ] TC-011: Brokerage History Navigation
- [ ] TC-012: Brokerage History List
- [ ] TC-013: Brokerage History Detail
- [ ] TC-014: Delete Note from History
- [ ] TC-015: Form Validation
- [ ] TC-016: Error Handling
- [ ] TC-017: Responsive Design
- [ ] TC-018: Currency Formatting
- [ ] TC-019: Empty States
- [ ] TC-020: Integration Flow - Complete Workflow

---

## Notes

- Picture field is now optional in user creation
- Application title: "D2X Money Manager"
- Backend must be running on port 8000
- Frontend runs on port 4400
- All tests should verify no console errors

