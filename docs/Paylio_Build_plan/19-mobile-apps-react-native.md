# Sprint 19 — Mobile Apps: iOS & Android (React Native)

**Duration: 8 days** (19a API layer: 2 days · 19b RN app: 5 days · 19c/19d push + shipping: 1 day).

## Objective
Native iOS and Android apps, backed by a JSON API layer on top of the existing Django backend — reusing its business logic, not reimplementing it.

## Preconditions
Sprint 17 complete (a deployed API host to point the mobile app at, rather than `localhost`).

## Firm Decisions
- Auth: **JWT via `djangorestframework-simplejwt`** — session-cookie auth (used by the web app) and JWT auth coexist as two separate `DEFAULT_AUTHENTICATION_CLASSES` entries; neither replaces the other.
- Mobile framework: **React Native via Expo**, not bare RN — Expo's tooling and EAS Build (cloud-built iOS binaries, no Mac required) are load-bearing decisions for a solo/small-team setup, not incidental.
- Data fetching: **`@tanstack/react-query`**, not raw `fetch` calls scattered through components — its `invalidateQueries` on mutation success is the mobile-side equivalent of the web app's `HX-Trigger: transactionsChanged` pattern (Sprint 7).
- Token storage: **`expo-secure-store`** only — never `AsyncStorage`, which is unencrypted.
- **DRF pagination applies only to `ModelViewSet`-backed endpoints** (`/transactions/`, `/categories/`, `/budgets/`), not to the function-based `@api_view` endpoints (`dashboard/summary/`, `advisor/feed/`, `rates/`) — the global `PAGE_SIZE=50` decision wraps list responses from viewsets in `{"count", "next", "previous", "results"}`, while the hand-built `Response(...)` calls in the function-based views return their dict/list exactly as written. **The RN `useTransactions()` hook must read `response.results`, not treat the response as a bare array** — this is a real, easy-to-miss integration bug given the two endpoint styles behave differently, called out explicitly here so it isn't discovered at runtime.
- `rates/` API endpoint is `AllowAny` (no auth required) — a deliberate, documented difference from Sprint 18's login-required HTML partial, so a logged-out mobile screen can still show live rates.
- Testing: Django/DRF side uses `pytest-django` + DRF's test client (same stack as every other sprint); RN side uses **Jest + React Native Testing Library** — introduced in this sprint specifically because it's the first sprint with JS code to test.

## Files (19a — API layer)
- `api/serializers.py`, `api/views.py`, `api/urls.py`
- `config/settings.py` (edit: `INSTALLED_APPS`, `REST_FRAMEWORK`, `SIMPLE_JWT`)
- `config/urls.py` (edit: include `api.urls` at `api/v1/`)
- `api/tests/test_views.py`

## Files (19b–19d — React Native app, separate project directory `mobile/`)
- `mobile/App.tsx`, `mobile/app.config.js`
- `mobile/src/api/client.ts`, `mobile/src/api/hooks.ts`
- `mobile/src/auth/AuthContext.tsx`
- `mobile/src/navigation/TabNavigator.tsx`
- `mobile/src/screens/LoginScreen.tsx`, `DashboardScreen.tsx`, `TransactionsScreen.tsx`, `BudgetsScreen.tsx`, `AdvisorScreen.tsx`, `RatesScreen.tsx`
- `mobile/src/api/__tests__/client.test.ts`
- `mobile/src/screens/__tests__/DashboardScreen.test.tsx`

## Classes & Functions (19a)
`api/serializers.py`, `api/views.py`, `api/urls.py` — exactly as specified in `spending-tracker-architecture.md` Step 19a: `TransactionSerializer`, `CategorySerializer`, `BudgetSerializer`, `InsightSerializer`, `AdviceMessageSerializer`, `UserRegistrationSerializer`; `TransactionViewSet`/`CategoryViewSet`/`BudgetViewSet` (each calling the same service functions the HTMX views use — `categorize()` from Sprint 8, not a reimplementation); `dashboard_summary`, `advisor_feed`, `advisor_refresh`, `metal_rates` as `@api_view` functions calling `dashboard.services.get_monthly_summary`, `advisor.rules.run_rules_for_user`, `advisor.ai.generate_advice`, and `rates.purity.compute_purity_rates` respectively; `RegisterView`; JWT routes via `TokenObtainPairView`/`TokenRefreshView`.

## Task Breakdown (19a)
1. `pip install djangorestframework djangorestframework-simplejwt`, `python manage.py startapp api`
2. `config/settings.py`: add `"rest_framework"` and `"api"` to `INSTALLED_APPS`; set `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = ["rest_framework_simplejwt.authentication.JWTAuthentication"]`; `SIMPLE_JWT` with 1-hour access / 14-day refresh, `ROTATE_REFRESH_TOKENS=True`
3. Write `api/serializers.py`, `api/views.py`, `api/urls.py` exactly per the architecture doc
4. Edit `config/urls.py`: `path("api/v1/", include("api.urls"))`
5. Write `api/tests/test_views.py`

## Testing Plan (19a)
`api/tests/test_views.py`:
- `test_register_creates_user`
- `test_token_obtain_returns_access_and_refresh_tokens`
- `test_transaction_list_requires_authentication` — no `Authorization` header, assert 401
- `test_transaction_list_is_paginated` — create 60 transactions, GET `/transactions/`, assert the response has `count == 60` and `results` has 50 entries (not a bare 60-item array) — the concrete regression test for the pagination-envelope decision above
- `test_transaction_create_via_api_uses_same_categorization_as_web` — POST a transaction with a Tier-2-keyword-matching merchant and no category, assert the returned category matches exactly what the web path (Sprint 7/8) would produce — direct proof the API isn't a parallel reimplementation
- `test_dashboard_summary_matches_service_function_directly` — call the endpoint and `dashboard.services.get_monthly_summary()` against identical fixture data, assert identical totals — a regression test specifically for logic drift between the web and API surfaces
- `test_metal_rates_endpoint_is_public` — GET with no `Authorization` header, assert 200 (confirms the `AllowAny` decision, and its documented contrast with Sprint 18's login-required HTML partial)

## Task Breakdown (19b)
1. `npx create-expo-app mobile`
2. `npx expo install expo-secure-store @react-navigation/native @react-navigation/bottom-tabs react-native-chart-kit`
3. `npm install @tanstack/react-query`
4. `npm install -D jest @testing-library/react-native @testing-library/jest-native`
5. Write `mobile/src/api/client.ts`, `hooks.ts` exactly per the architecture doc, **with `useTransactions()` reading `response.results`** per the Firm Decisions note above
6. Write `mobile/src/auth/AuthContext.tsx` — holds tokens (via `client.ts`'s `SecureStore` calls), exposes `login()`/`logout()`, gates `TabNavigator` behind an authenticated check
7. Write `mobile/src/navigation/TabNavigator.tsx` — five tabs (Dashboard, Transactions, Budgets, Advisor, Rates)
8. Write all six screens
9. Write the two test files listed above

## Testing Plan (19b)
`mobile/src/api/__tests__/client.test.ts` (Jest, mocking `expo-secure-store` and global `fetch`):
- `test('attaches Authorization header when a token is stored')` — mock `SecureStore.getItemAsync` to resolve a token, call `api.get(...)`, assert the mocked `fetch` was called with the matching `Authorization: Bearer ...` header
- `test('omits Authorization header when no token is stored')` — mock `SecureStore.getItemAsync` to resolve `null`, assert no `Authorization` header is present in the mocked `fetch` call

`mobile/src/screens/__tests__/DashboardScreen.test.tsx` (React Native Testing Library):
- `test('renders the total spent value from useDashboardSummary')` — mock the hook's return value directly (not the network layer), render `<DashboardScreen />`, assert the total appears in the rendered tree

## Task Breakdown (19c — push notifications)
1. `npx expo install expo-notifications`
2. Add a `DeviceToken(user, expo_push_token)` model to the `accounts` or `api` app; register the token from the RN app right after login
3. Edit `advisor/tasks.py`'s `run_daily_insights`: when a newly created `Insight.severity == Insight.CRITICAL`, call Expo's push API with the user's stored token — reuses the existing trigger point, no second notification pipeline built

## Task Breakdown (19d — shipping)
1. `npm install -g eas-cli`
2. `eas build --platform ios` and `eas build --platform android` — `EXPO_PUBLIC_API_BASE_URL` pointed at the Sprint 17 deployed host, never `localhost`
3. Confirm an active Apple Developer account and Google Play Developer registration exist before submission; budget calendar time separately for both stores' review processes — a fundamentally different release cadence from "push to the Django server"

## Load & Scale
- Pagination envelope handling (above) is this sprint's most concrete load-related decision — without it, a user with more than 50 transactions would see a broken or silently-truncated transaction list on mobile the moment `PAGE_SIZE` is hit.
- `useMetalRates()` polls at the same 5-minute interval as the web widget (Sprint 18) — kept identical across platforms deliberately, so the two surfaces never show visibly different "freshness" to a user checking both.
- The JWT access-token lifetime (1 hour) balances security against how often the mobile app needs a silent refresh — refresh tokens (14 days) mean a user isn't forced to re-enter credentials on every app open within that window.

## Definition of Done
- All 19a and 19b tests pass
- `npx expo start` runs the app locally against a real (or local) deployed API; login, viewing the dashboard, adding a transaction, and viewing live metal rates all work end-to-end on both an iOS simulator and an Android emulator
- At least one successful `eas build` completes for each platform before attempting store submission
