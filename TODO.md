# TODO - Brazcom ISP Billing System

## ✅ Completed Tasks

### Backend API Fixes
- [x] Fix 404 errors for bank accounts routes
- [x] Fix 404 errors for receivables routes
- [x] Add proper Pydantic response models (ReceivableResponse, BankAccountResponse)
- [x] Enable redirect_slashes=True to handle URLs with/without trailing slashes
- [x] Fix SQLAlchemy relationship ambiguity in BankAccount model (foreign_keys specification)
- [x] Fix Pydantic datetime validation errors (use datetime type instead of str)
- [x] Verify routes appear in OpenAPI documentation
- [x] Confirm routes return 401 (authentication required) instead of 404

### Sicoob Integration
- [x] Create SicoobGateway service with sandbox credentials
- [x] Implement boleto registration API calls
- [x] Create BillingService for automatic receivable registration
- [x] Test basic API communication and data preparation
- [x] Fix datetime handling in boleto preparation

## 🔄 Next Steps

### Testing & Validation
- [ ] Test routes with authenticated requests (need JWT tokens)
- [ ] Initialize billing permissions if needed (billing_view, billing_manage)
- [ ] Run frontend locally to verify API integration
- [ ] Test Sicoob boleto registration with real client data
- [ ] Implement webhook endpoint for payment notifications
- [ ] Test boleto consultation and status updates
- [ ] Test end-to-end billing workflow

### Database & Migrations
- [ ] Verify database schema is up-to-date for billing tables
- [ ] Check if any migrations need to be applied

### Documentation
- [ ] Update API documentation with billing endpoints
- [ ] Add usage examples for billing operations

## 📋 Notes

- Routes now properly registered and documented in OpenAPI
- All routes return 401 (authentication required) as expected
- Frontend pages and services were already implemented in previous sessions
- Database models and services are ready for billing operations